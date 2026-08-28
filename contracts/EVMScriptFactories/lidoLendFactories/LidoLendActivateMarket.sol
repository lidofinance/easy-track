// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to activate a deployed Lido Lend market
contract LidoLendActivateMarket is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    struct ActivationParams {
        MarketParams marketParams;
        address irmConfig;
        address controller;
        bool enableSettlement;
        address steward;
        address pauserCommittee;
        ILidoLendERC4626 preseedVault;
        uint256 fee;
    }

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
    string private constant ERROR_OWNER_NOT_MANAGER = "OWNER_NOT_MANAGER";
    string private constant ERROR_DASHBOARD_NOT_MANAGER = "DASHBOARD_NOT_MANAGER";
    string private constant ERROR_OWNER_NOT_UNFREEZER = "OWNER_NOT_UNFREEZER";
    string private constant ERROR_DASHBOARD_NOT_FREEZER = "DASHBOARD_NOT_FREEZER";
    string private constant ERROR_CIRCUIT_BREAKER_NOT_PAUSER = "CIRCUIT_BREAKER_NOT_PAUSER";

    // -------------
    // CONSTANTS
    // -------------

    int256 private constant WAD = 1e18;
    uint256 private constant CALLS_COUNT_WITH_SET_FEE = 7;
    uint256 private constant CALLS_COUNT_WITHOUT_SET_FEE = 6;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the IrmRouter
    address public immutable irmRouter;
    /// @notice Address of the configurable IRM used by this factory
    address public immutable configurableIrm;
    /// @notice Address of the CircuitBreaker instance
    address public immutable circuitBreaker;
    /// @notice Address of the RiskStewardDashboard instance
    address public immutable riskStewardDashboard;
    /// @notice Address of the Lido Lend preseeder
    address public immutable lidoLendPreseeder;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _lidoLendOwner,
        address _irmRouter,
        address _configurableIrm,
        address _circuitBreaker,
        address _riskStewardDashboard,
        address _lidoLendPreseeder
    ) LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner) {
        irmRouter = _irmRouter;
        configurableIrm = _configurableIrm;
        circuitBreaker = _circuitBreaker;
        riskStewardDashboard = _riskStewardDashboard;
        lidoLendPreseeder = _lidoLendPreseeder;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to activate a deployed Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData ABI-encoded ActivationParams
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        ActivationParams memory params = decodeEVMScriptCallData(_evmScriptCallData);
        _validateActivation(params);
        return _createActivationScript(params);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData ABI-encoded ActivationParams
    /// @return params Decoded market activation and preseeding parameters
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (ActivationParams memory params)
    {
        return abi.decode(_evmScriptCallData, (ActivationParams));
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createActivationScript(ActivationParams memory params)
        private
        view
        returns (bytes memory)
    {
        bytes32 marketId = keccak256(abi.encode(params.marketParams));
        bool shouldSetFee = params.fee != 0;
        uint256 callsCount = shouldSetFee ? CALLS_COUNT_WITH_SET_FEE : CALLS_COUNT_WITHOUT_SET_FEE;
        address[] memory to = new address[](callsCount);
        bytes4[] memory methodIds = new bytes4[](callsCount);
        bytes[] memory callData = new bytes[](callsCount);

        to[0] = configurableIrm;
        methodIds[0] = IConfigurableIrm.applyIrmConfig.selector;
        callData[0] = abi.encode(params.marketParams, params.irmConfig);

        to[1] = irmRouter;
        methodIds[1] = IIrmRouter.setMarketIrm.selector;
        callData[1] = abi.encode(params.marketParams, configurableIrm);

        to[2] = lidoLendOwner;
        methodIds[2] = ILidoLendOwner.createMarket.selector;
        callData[2] = abi.encode(params.marketParams, params.controller, params.enableSettlement);

        to[3] = riskStewardDashboard;
        methodIds[3] = IRiskStewardDashboard.addMarketSteward.selector;
        callData[3] = abi.encode(marketId, params.steward);

        to[4] = circuitBreaker;
        methodIds[4] = ICircuitBreaker.registerPauser.selector;
        callData[4] = abi.encode(params.controller, params.pauserCommittee);

        to[5] = lidoLendPreseeder;
        methodIds[5] = ILidoLendPreseeder.preseedMarket.selector;
        callData[5] = abi.encode(params.marketParams, params.preseedVault);

        if (shouldSetFee) {
            to[6] = lidoLendOwner;
            methodIds[6] = ILidoLendOwner.setFee.selector;
            callData[6] = abi.encode(params.marketParams, params.fee);
        }

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    function _validateActivation(ActivationParams memory params) private view {
        require(params.marketParams.loanToken != address(0), ERROR_ZERO_LOAN_TOKEN);
        require(params.marketParams.collateralToken != address(0), ERROR_ZERO_COLLATERAL_TOKEN);
        require(params.marketParams.oracle != address(0), ERROR_ZERO_ORACLE);
        require(params.irmConfig != address(0), ERROR_ZERO_IRM_CONFIG);
        require(params.controller != address(0), ERROR_ZERO_CONTROLLER);
        require(params.steward != address(0), ERROR_ZERO_STEWARD);
        require(params.pauserCommittee != address(0), ERROR_ZERO_PAUSER_COMMITTEE);
        require(params.marketParams.lltv < uint256(WAD), ERROR_MAX_LLTV_EXCEEDED);
        require(params.fee <= MAX_FEE, ERROR_MAX_FEE_EXCEEDED);
        require(params.marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);
        bytes32 marketId = keccak256(abi.encode(params.marketParams));
        ILidoLend core = ILidoLend(lidoLend);
        require(core.market(marketId).lastUpdate == 0, ERROR_MARKET_ALREADY_CREATED);
        ILidoLendMarketController marketController = ILidoLendMarketController(params.controller);
        require(marketController.marketId() == marketId, ERROR_CONTROLLER_MISMATCH);
        require(marketController.LIDO_LEND() == core, ERROR_CONTROLLER_CORE_MISMATCH);
        require(
            marketController.hasRole(marketController.MANAGER_ROLE(), lidoLendOwner),
            ERROR_OWNER_NOT_MANAGER
        );
        require(
            marketController.hasRole(marketController.MANAGER_ROLE(), riskStewardDashboard),
            ERROR_DASHBOARD_NOT_MANAGER
        );
        require(
            marketController.hasRole(marketController.UNFREEZER_ROLE(), lidoLendOwner),
            ERROR_OWNER_NOT_UNFREEZER
        );
        require(
            marketController.hasRole(marketController.FREEZER_ROLE(), riskStewardDashboard),
            ERROR_DASHBOARD_NOT_FREEZER
        );
        require(
            marketController.hasRole(marketController.PAUSER_ROLE(), circuitBreaker),
            ERROR_CIRCUIT_BREAKER_NOT_PAUSER
        );
        ILidoLendPreseeder(lidoLendPreseeder).validatePreseed(
            params.marketParams,
            params.preseedVault
        );
    }
}
