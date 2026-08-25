// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to activate a deployed Lido Lend market
contract LidoLendActivateMarket is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_LOAN_TOKEN = "ZERO_LOAN_TOKEN";
    string private constant ERROR_ZERO_COLLATERAL_TOKEN = "ZERO_COLLATERAL_TOKEN";
    string private constant ERROR_ZERO_ORACLE = "ZERO_ORACLE";
    string private constant ERROR_ZERO_IRM_CONFIG = "ZERO_IRM_CONFIG";
    string private constant ERROR_ZERO_CONTROLLER = "ZERO_CONTROLLER";
    string private constant ERROR_ZERO_STEWARD = "ZERO_STEWARD";
    string private constant ERROR_ZERO_PAUSER_COMMITTEE = "ZERO_PAUSER_COMMITTEE";
    string private constant ERROR_MAX_LLTV_EXCEEDED = "MAX_LLTV_EXCEEDED";
    string private constant ERROR_MAX_FEE_EXCEEDED = "MAX_FEE_EXCEEDED";
    string private constant ERROR_IRM_NOT_ROUTER = "IRM_NOT_ROUTER";
    string private constant ERROR_MARKET_ALREADY_CREATED = "MARKET_ALREADY_CREATED";
    string private constant ERROR_CONTROLLER_MISMATCH = "CONTROLLER_MISMATCH";
    string private constant ERROR_CONTROLLER_CORE_MISMATCH = "CONTROLLER_CORE_MISMATCH";
    string private constant ERROR_CIRCUIT_BREAKER_NOT_PAUSER = "CIRCUIT_BREAKER_NOT_PAUSER";

    // -------------
    // CONSTANTS
    // -------------

    int256 private constant WAD = 1e18;
    // Mirrors MAX_FEE in lido-lend/src/libraries/ConstantsLib.sol.
    uint256 private constant MAX_FEE = 0.25e18;

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
    ///        address steward, address pauserCommittee, bool enableSettlement, uint256 fee)
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
            bool enableSettlement,
            uint256 fee
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        _validateActivation(marketParams, irmConfig, controller, steward, pauserCommittee, fee);

        return
            _createActivationScript(
                marketParams,
                irmConfig,
                controller,
                steward,
                pauserCommittee,
                enableSettlement,
                fee
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple:
    ///        (MarketParams marketParams, address irmConfig, address controller,
    ///        address steward, address pauserCommittee, bool enableSettlement, uint256 fee)
    /// @return marketParams Market params of the market to activate
    /// @return irmConfig Address of the config applied to the AdaptiveCurveIrm singleton
    /// @return controller Address of the market's controller
    /// @return steward Address appointed as the market steward
    /// @return pauserCommittee Address of the pauser committee
    /// @return enableSettlement Settlement queue enabled
    /// @return fee Initial market fee; zero keeps the core default
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            MarketParams memory marketParams,
            address irmConfig,
            address controller,
            address steward,
            address pauserCommittee,
            bool enableSettlement,
            uint256 fee
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createActivationScript(
        MarketParams memory marketParams,
        address irmConfig,
        address controller,
        address steward,
        address pauserCommittee,
        bool enableSettlement,
        uint256 fee
    ) private view returns (bytes memory) {
        bytes32 marketId = keccak256(abi.encode(marketParams));
        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        uint256 callsCount = fee == 0 ? 5 : 6;
        address[] memory to = new address[](callsCount);
        bytes4[] memory methodIds = new bytes4[](callsCount);
        bytes[] memory callData = new bytes[](callsCount);

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
        methodIds[3] = IRiskStewardDashboard.addMarketSteward.selector;
        callData[3] = abi.encode(marketId, steward);

        to[4] = circuitBreaker;
        methodIds[4] = ICircuitBreaker.registerPauser.selector;
        callData[4] = abi.encode(controller, pauserCommittee);

        if (fee != 0) {
            to[5] = lidoLendOwner;
            methodIds[5] = owner.setFee.selector;
            callData[5] = abi.encode(marketParams, fee);
        }

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            MarketParams memory marketParams,
            address irmConfig,
            address controller,
            address steward,
            address pauserCommittee,
            bool enableSettlement,
            uint256 fee
        )
    {
        return
            abi.decode(
                _evmScriptCallData,
                (MarketParams, address, address, address, address, bool, uint256)
            );
    }

    function _validateActivation(
        MarketParams memory marketParams,
        address irmConfig,
        address controller,
        address steward,
        address pauserCommittee,
        uint256 fee
    ) private view {
        require(marketParams.loanToken != address(0), ERROR_ZERO_LOAN_TOKEN);
        require(marketParams.collateralToken != address(0), ERROR_ZERO_COLLATERAL_TOKEN);
        require(marketParams.oracle != address(0), ERROR_ZERO_ORACLE);
        require(irmConfig != address(0), ERROR_ZERO_IRM_CONFIG);
        require(controller != address(0), ERROR_ZERO_CONTROLLER);
        require(steward != address(0), ERROR_ZERO_STEWARD);
        require(pauserCommittee != address(0), ERROR_ZERO_PAUSER_COMMITTEE);
        require(marketParams.lltv < uint256(WAD), ERROR_MAX_LLTV_EXCEEDED);
        require(fee <= MAX_FEE, ERROR_MAX_FEE_EXCEEDED);
        require(marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);
        bytes32 marketId = keccak256(abi.encode(marketParams));
        ILidoLend core = ILidoLendOwner(lidoLendOwner).LIDO_LEND();
        require(core.market(marketId).lastUpdate == 0, ERROR_MARKET_ALREADY_CREATED);
        ILidoLendMarketController marketController = ILidoLendMarketController(controller);
        require(marketController.marketId() == marketId, ERROR_CONTROLLER_MISMATCH);
        require(marketController.LIDO_LEND() == core, ERROR_CONTROLLER_CORE_MISMATCH);
        require(
            marketController.hasRole(marketController.PAUSER_ROLE(), circuitBreaker),
            ERROR_CIRCUIT_BREAKER_NOT_PAUSER
        );
    }
}
