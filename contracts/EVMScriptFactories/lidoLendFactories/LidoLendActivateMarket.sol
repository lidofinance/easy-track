// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to activate a deployed Lido Lend market
/// @dev The market's IRM curve is the domain's `AdaptiveCurveIrm` SINGLETON (an immutable here, not motion
///      calldata): one instance serves every market, and the per-market config is applied by the motion
///      itself. The call order is mandatory, not stylistic: `applyIrmConfig` and `setMarketIrm` must both
///      precede `createMarket`, whose first `borrowRate` ping reverts while the market is unrouted or its
///      config is unset. The market steward is appointed only after the market is created. Exit-book
///      allow-listing is deliberately NOT part of this motion — not
///      every market gets exit books; it runs separately via the dedicated exit-book factories.
contract LidoLendActivateMarket is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_LOAN_TOKEN = "ZERO_LOAN_TOKEN";
    string private constant ERROR_ZERO_COLLATERAL_TOKEN = "ZERO_COLLATERAL_TOKEN";
    string private constant ERROR_ZERO_ORACLE = "ZERO_ORACLE";
    string private constant ERROR_ZERO_CONTROLLER = "ZERO_CONTROLLER";
    string private constant ERROR_ZERO_STEWARD = "ZERO_STEWARD";
    string private constant ERROR_ZERO_PAUSER_COMMITTEE = "ZERO_PAUSER_COMMITTEE";
    string private constant ERROR_MAX_LLTV_EXCEEDED = "MAX_LLTV_EXCEEDED";
    string private constant ERROR_IRM_NOT_ROUTER = "IRM_NOT_ROUTER";
    string private constant ERROR_MARKET_ALREADY_CREATED = "MARKET_ALREADY_CREATED";
    string private constant ERROR_CONTROLLER_MISMATCH = "CONTROLLER_MISMATCH";
    string private constant ERROR_CIRCUIT_BREAKER_NOT_PAUSER = "CIRCUIT_BREAKER_NOT_PAUSER";

    // -------------
    // CONSTANTS
    // -------------

    int256 private constant WAD = 1e18;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLendOwner facade
    address public immutable lidoLendOwner;
    /// @notice Address of the IrmRouter
    address public immutable irmRouter;
    /// @notice Address of the domain's AdaptiveCurveIrm singleton (serves every market)
    address public immutable adaptiveCurveIrm;
    /// @notice Address of the CircuitBreaker instance
    address public immutable circuitBreaker;
    /// @notice Address of the RiskStewardDashboard instance
    address public immutable riskStewardDashboard;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _lidoLendOwner,
        address _irmRouter,
        address _adaptiveCurveIrm,
        address _circuitBreaker,
        address _riskStewardDashboard
    ) TrustedCaller(_trustedCaller) {
        lidoLendOwner = _lidoLendOwner;
        irmRouter = _irmRouter;
        adaptiveCurveIrm = _adaptiveCurveIrm;
        circuitBreaker = _circuitBreaker;
        riskStewardDashboard = _riskStewardDashboard;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to activate a deployed Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple:
    ///        (MarketParams marketParams, address irmConfig, address controller,
    ///        address steward, address pauserCommittee, bool enableSettlement)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            MarketParams memory marketParams,
            address irmConfig,
            address controller,
            address steward,
            address pauserCommittee,
            bool enableSettlement
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(marketParams.loanToken != address(0), ERROR_ZERO_LOAN_TOKEN);
        require(marketParams.collateralToken != address(0), ERROR_ZERO_COLLATERAL_TOKEN);
        require(marketParams.oracle != address(0), ERROR_ZERO_ORACLE);
        require(controller != address(0), ERROR_ZERO_CONTROLLER);
        require(steward != address(0), ERROR_ZERO_STEWARD);
        require(pauserCommittee != address(0), ERROR_ZERO_PAUSER_COMMITTEE);
        require(marketParams.lltv < uint256(WAD), ERROR_MAX_LLTV_EXCEEDED);
        // The market id commits to the `irm` field; anything but the domain's router is a phantom market that
        // `setMarketIrm` would reject at enactment anyway — fail at motion creation instead.
        require(marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);
        bytes32 marketId = keccak256(abi.encode(marketParams));
        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        require(owner.LIDO_LEND().market(marketId).lastUpdate == 0, ERROR_MARKET_ALREADY_CREATED);
        ILidoLendMarketController marketController = ILidoLendMarketController(controller);
        require(marketController.marketId() == marketId, ERROR_CONTROLLER_MISMATCH);
        require(
            marketController.hasRole(marketController.PAUSER_ROLE(), circuitBreaker),
            ERROR_CIRCUIT_BREAKER_NOT_PAUSER
        );
        IRiskStewardDashboard dashboard = IRiskStewardDashboard(riskStewardDashboard);
        address[] memory to = new address[](5);
        bytes4[] memory methodIds = new bytes4[](5);
        bytes[] memory callData = new bytes[](5);

        // Both the config and routing must be in place BEFORE createMarket: its first borrowRate ping
        // reverts on an unrouted market or an unset IRM config.
        to[0] = adaptiveCurveIrm;
        methodIds[0] = IConfigurableIrm.applyIrmConfig.selector;
        callData[0] = abi.encode(marketParams, irmConfig);

        to[1] = irmRouter;
        methodIds[1] = IIrmRouter.setMarketIrm.selector;
        callData[1] = abi.encode(marketParams, adaptiveCurveIrm);

        to[2] = lidoLendOwner;
        methodIds[2] = owner.createMarket.selector;
        callData[2] = abi.encode(marketParams, controller, enableSettlement);

        to[3] = riskStewardDashboard;
        methodIds[3] = dashboard.addMarketSteward.selector;
        callData[3] = abi.encode(marketId, steward);

        to[4] = circuitBreaker;
        methodIds[4] = ICircuitBreaker.registerPauser.selector;
        callData[4] = abi.encode(controller, pauserCommittee);

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple:
    ///        (MarketParams marketParams, address irmConfig, address controller,
    ///        address steward, address pauserCommittee, bool enableSettlement)
    /// @return marketParams Market params of the market to activate
    /// @return irmConfig Address of the config applied to the AdaptiveCurveIrm singleton
    /// @return controller Address of the market's controller
    /// @return steward Address appointed as the market steward
    /// @return pauserCommittee Address of the pauser committee
    /// @return enableSettlement Settlement queue enabled
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            MarketParams memory marketParams,
            address irmConfig,
            address controller,
            address steward,
            address pauserCommittee,
            bool enableSettlement
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            MarketParams memory marketParams,
            address irmConfig,
            address controller,
            address steward,
            address pauserCommittee,
            bool enableSettlement
        )
    {
        (marketParams, irmConfig, controller, steward, pauserCommittee, enableSettlement) = abi
            .decode(_evmScriptCallData, (MarketParams, address, address, address, address, bool));
    }
}
