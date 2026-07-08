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
    string private constant ERROR_ZERO_IRM = "ZERO_IRM";
    string private constant ERROR_ZERO_CURVE = "ZERO_CURVE";
    string private constant ERROR_ZERO_CONTROLLER = "ZERO_CONTROLLER";
    string private constant ERROR_ZERO_PAUSER_COMMITTEE = "ZERO_PAUSER_COMMITTEE";
    string private constant ERROR_MAX_LLTV_EXCEEDED = "MAX_LLTV_EXCEEDED";
    string private constant ERROR_CONTROLLER_MISMATCH = "CONTROLLER_MISMATCH";

    uint256 private constant WAD = 1e18;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLendOwner facade
    ILidoLendOwner public immutable lidoLendOwner;
    /// @notice Address of the IrmRouter
    address public immutable irmRouter;
    /// @notice Address of the CircuitBreaker instance
    address public immutable circuitBreaker;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner, address _irmRouter, address _circuitBreaker)
        TrustedCaller(_trustedCaller)
    {
        lidoLendOwner = ILidoLendOwner(_lidoLendOwner);
        irmRouter = _irmRouter;
        circuitBreaker = _circuitBreaker;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to activate a deployed Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple:
    ///        (MarketParams marketParams, address curve, address controller, address pauserCommittee,
    ///        bool enableSettlement)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            MarketParams memory marketParams,
            address curve,
            address controller,
            address pauserCommittee,
            bool enableSettlement
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(marketParams.loanToken != address(0), ERROR_ZERO_LOAN_TOKEN);
        require(marketParams.collateralToken != address(0), ERROR_ZERO_COLLATERAL_TOKEN);
        require(marketParams.oracle != address(0), ERROR_ZERO_ORACLE);
        require(marketParams.irm != address(0), ERROR_ZERO_IRM);
        require(curve != address(0), ERROR_ZERO_CURVE);
        require(controller != address(0), ERROR_ZERO_CONTROLLER);
        require(pauserCommittee != address(0), ERROR_ZERO_PAUSER_COMMITTEE);
        require(marketParams.lltv < WAD, ERROR_MAX_LLTV_EXCEEDED);
        require(
            ILidoLendMarketController(controller).marketId() == keccak256(abi.encode(marketParams)),
            ERROR_CONTROLLER_MISMATCH
        );

        address[] memory to = new address[](3);
        bytes4[] memory methodIds = new bytes4[](3);
        bytes[] memory callData = new bytes[](3);

        to[0] = irmRouter;
        methodIds[0] = IIrmRouter.setMarketIrm.selector;
        callData[0] = abi.encode(marketParams, curve);

        to[1] = address(lidoLendOwner);
        methodIds[1] = lidoLendOwner.createMarket.selector;
        callData[1] = abi.encode(marketParams, controller, enableSettlement);

        to[2] = circuitBreaker;
        methodIds[2] = ICircuitBreaker.registerPauser.selector;
        callData[2] = abi.encode(controller, pauserCommittee);

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple:
    ///        (MarketParams marketParams, address curve, address controller, address pauserCommittee,
    ///        bool enableSettlement)
    /// @return marketParams Market params of the market to activate
    /// @return curve Address of the market's IRM curve
    /// @return controller Address of the market's controller
    /// @return pauserCommittee Address of the pauser committee
    /// @return enableSettlement Whether the market is created with the settlement queue enabled
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            MarketParams memory marketParams,
            address curve,
            address controller,
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
            address curve,
            address controller,
            address pauserCommittee,
            bool enableSettlement
        )
    {
        (marketParams, curve, controller, pauserCommittee, enableSettlement) =
            abi.decode(_evmScriptCallData, (MarketParams, address, address, address, bool));
    }
}
