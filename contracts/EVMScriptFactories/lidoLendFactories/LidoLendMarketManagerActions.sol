// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScripts for Lido Lend market-management and fee actions routed through LidoLendOwner
contract LidoLendMarketManagerActions is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    /// @dev Action ordinals are part of the calldata ABI. Never reorder existing members; append only.
    enum Action {
        SetInstantActivation,
        SetCollateralActivationConfig,
        SetSettlementConfig,
        SetSupplyCap,
        UnfreezeMarkets,
        SetFee
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";
    string private constant ERROR_ZERO_CALLER = "ZERO_CALLER";
    string private constant ERROR_SAME_INSTANT_ACTIVATION_STATUS = "SAME_INSTANT_ACTIVATION_STATUS";
    string private constant ERROR_SAME_CONFIG = "SAME_CONFIG";
    string private constant ERROR_ZERO_MIN_ACTIVATION_DELAY = "ZERO_MIN_ACTIVATION_DELAY";
    string private constant ERROR_INVALID_ACTIVATION_DELAYS = "INVALID_ACTIVATION_DELAYS";
    string private constant ERROR_MAX_ACTIVATION_DELAY_EXCEEDED = "MAX_ACTIVATION_DELAY_EXCEEDED";
    string private constant ERROR_MAX_ACTIVATING_LOCK_DURATION_EXCEEDED =
        "MAX_ACTIVATING_LOCK_DURATION_EXCEEDED";
    string private constant ERROR_INVALID_MAX_GUARDIANS_QUORUM_DELAY =
        "INVALID_MAX_GUARDIANS_QUORUM_DELAY";
    string private constant ERROR_MAX_GUARDIANS_QUORUM_DELAY_EXCEEDED =
        "MAX_GUARDIANS_QUORUM_DELAY_EXCEEDED";
    string private constant ERROR_ZERO_MIN_ACTIVATION_AMOUNT = "ZERO_MIN_ACTIVATION_AMOUNT";
    string private constant ERROR_ZERO_MAX_DELAY_INFLOW = "ZERO_MAX_DELAY_INFLOW";
    string private constant ERROR_INVALID_MIN_DEPOSIT_AMOUNT = "INVALID_MIN_DEPOSIT_AMOUNT";
    string private constant ERROR_MAX_DELAY_PER_STRIKE_EXCEEDED = "MAX_DELAY_PER_STRIKE_EXCEEDED";
    string private constant ERROR_MAX_DELAY_PER_SUSPECT_EXCEEDED = "MAX_DELAY_PER_SUSPECT_EXCEEDED";
    string private constant ERROR_SETTLEMENT_CONFIG_OUT_OF_RANGE = "SETTLEMENT_CONFIG_OUT_OF_RANGE";
    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_FEE_ALREADY_SET = "FEE_ALREADY_SET";
    string private constant ERROR_MAX_FEE_EXCEEDED = "MAX_FEE_EXCEEDED";

    // -------------
    // CONSTANTS
    // -------------

    uint256 private constant BPS = 10_000;
    // Mirrors MAX_DELAY_DURATION in lido-lend-markets/src/libs/CollateralActivationLib.sol.
    uint256 private constant MAX_DELAY_DURATION = 7 days;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript for one market-management or fee action
    /// @param _creator Address that creates the EVMScript
    /// @param _evmScriptCallData Encoded envelope: abi.encode(Action action, bytes payload)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (Action action, bytes memory payload) = decodeEVMScriptCallData(_evmScriptCallData);

        if (action == Action.SetInstantActivation) {
            return _createSetInstantActivationEVMScript(payload);
        }
        if (action == Action.SetCollateralActivationConfig) {
            return _createSetCollateralActivationConfigEVMScript(payload);
        }
        if (action == Action.SetSettlementConfig) {
            return _createSetSettlementConfigEVMScript(payload);
        }
        if (action == Action.SetSupplyCap) {
            return _createSetSupplyCapEVMScript(payload);
        }
        if (action == Action.UnfreezeMarkets) {
            return _createUnfreezeMarketsEVMScript(payload);
        }
        if (action == Action.SetFee) {
            return _createSetFeeEVMScript(payload);
        }
        revert(ERROR_INVALID_ACTION);
    }

    // -------------
    // PUBLIC DECODERS
    // -------------

    /// @notice Decodes the outer action envelope used by createEVMScript
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (Action action, bytes memory payload)
    {
        (action, payload) = abi.decode(_evmScriptCallData, (Action, bytes));
    }

    /// @notice Decodes a SetInstantActivation payload
    function decodeSetInstantActivationPayload(bytes memory _payload)
        public
        pure
        returns (
            bytes32 marketId,
            address caller,
            bool enabled
        )
    {
        (marketId, caller, enabled) = abi.decode(_payload, (bytes32, address, bool));
    }

    /// @notice Decodes a SetCollateralActivationConfig payload
    function decodeSetCollateralActivationConfigPayload(bytes memory _payload)
        public
        pure
        returns (
            bytes32 marketId,
            ILidoLendMarketController.CollateralActivationConfig memory newCfg
        )
    {
        (marketId, newCfg) = abi.decode(
            _payload,
            (bytes32, ILidoLendMarketController.CollateralActivationConfig)
        );
    }

    /// @notice Decodes a SetSettlementConfig payload
    function decodeSetSettlementConfigPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, ILidoLendMarketController.SettlementConfig memory newConfig)
    {
        (marketId, newConfig) = abi.decode(
            _payload,
            (bytes32, ILidoLendMarketController.SettlementConfig)
        );
    }

    /// @notice Decodes a SetSupplyCap payload
    function decodeSetSupplyCapPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, uint256 newCap)
    {
        (marketId, newCap) = abi.decode(_payload, (bytes32, uint256));
    }

    /// @notice Decodes an UnfreezeMarkets payload
    function decodeUnfreezeMarketsPayload(bytes memory _payload)
        public
        pure
        returns (bytes32[] memory marketIds)
    {
        marketIds = abi.decode(_payload, (bytes32[]));
    }

    /// @notice Decodes a SetFee payload
    function decodeSetFeePayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, uint256 newFee)
    {
        (marketId, newFee) = abi.decode(_payload, (bytes32, uint256));
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createSetInstantActivationEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address caller, bool enabled) = decodeSetInstantActivationPayload(
            _payload
        );
        require(caller != address(0), ERROR_ZERO_CALLER);

        ILidoLendMarketController marketController = _getMarketControllerOrRevert(marketId);
        require(
            marketController.hasInstantActivation(caller) != enabled,
            ERROR_SAME_INSTANT_ACTIVATION_STATUS
        );

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.setInstantActivation.selector,
                abi.encode(marketId, caller, enabled)
            );
    }

    function _createSetCollateralActivationConfigEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (
            bytes32 marketId,
            ILidoLendMarketController.CollateralActivationConfig memory newCfg
        ) = decodeSetCollateralActivationConfigPayload(_payload);
        ILidoLendMarketController marketController = _getMarketControllerOrRevert(marketId);

        _validateCollateralActivationConfig(newCfg);
        require(
            keccak256(abi.encode(newCfg)) !=
                keccak256(abi.encode(marketController.collateralActivationConfig())),
            ERROR_SAME_CONFIG
        );

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.setMarketCollateralActivationConfig.selector,
                abi.encode(marketId, newCfg)
            );
    }

    function _createSetSettlementConfigEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (
            bytes32 marketId,
            ILidoLendMarketController.SettlementConfig memory newConfig
        ) = decodeSetSettlementConfigPayload(_payload);
        ILidoLendMarketController marketController = _getMarketControllerOrRevert(marketId);

        require(
            newConfig.sliceFloorBps <= BPS && newConfig.ltvStepBps <= BPS,
            ERROR_SETTLEMENT_CONFIG_OUT_OF_RANGE
        );
        require(
            keccak256(abi.encode(newConfig)) !=
                keccak256(abi.encode(marketController.settlementConfig())),
            ERROR_SAME_CONFIG
        );

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.setMarketSettlementConfig.selector,
                abi.encode(marketId, newConfig)
            );
    }

    function _createSetSupplyCapEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newCap) = decodeSetSupplyCapPayload(_payload);

        _getMarketControllerOrRevert(marketId);

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.setMarketSupplyCap.selector,
                abi.encode(marketId, newCap)
            );
    }

    function _createUnfreezeMarketsEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        bytes32[] memory marketIds = decodeUnfreezeMarketsPayload(_payload);
        require(marketIds.length > 0, ERROR_EMPTY_MARKETS_LIST);

        bytes[] memory encodedCalldata = new bytes[](marketIds.length);
        for (uint256 i = 0; i < marketIds.length; ++i) {
            _getMarketControllerOrRevert(marketIds[i]);
            encodedCalldata[i] = abi.encode(marketIds[i]);
        }

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.unfreezeMarket.selector,
                encodedCalldata
            );
    }

    function _createSetFeeEVMScript(bytes memory _payload) private view returns (bytes memory) {
        (bytes32 marketId, uint256 newFee) = decodeSetFeePayload(_payload);
        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        ILidoLend core = ILidoLend(lidoLend);
        Market memory currentMarket = core.market(marketId);
        require(currentMarket.lastUpdate != 0, ERROR_MARKET_NOT_FOUND);
        require(currentMarket.fee != newFee, ERROR_FEE_ALREADY_SET);
        require(newFee <= MAX_FEE, ERROR_MAX_FEE_EXCEEDED);

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setFee.selector,
                abi.encode(core.idToMarketParams(marketId), newFee)
            );
    }

    function _validateCollateralActivationConfig(
        ILidoLendMarketController.CollateralActivationConfig memory cfg
    ) private pure {
        require(cfg.minActivationDelay != 0, ERROR_ZERO_MIN_ACTIVATION_DELAY);
        require(cfg.minActivationDelay <= cfg.maxActivationDelay, ERROR_INVALID_ACTIVATION_DELAYS);
        require(cfg.maxActivationDelay <= MAX_DELAY_DURATION, ERROR_MAX_ACTIVATION_DELAY_EXCEEDED);
        require(
            cfg.activatingLockDuration <= MAX_DELAY_DURATION,
            ERROR_MAX_ACTIVATING_LOCK_DURATION_EXCEEDED
        );
        require(
            cfg.maxGuardiansQuorumDelay == 0 ||
                cfg.maxGuardiansQuorumDelay > cfg.maxActivationDelay,
            ERROR_INVALID_MAX_GUARDIANS_QUORUM_DELAY
        );
        require(
            cfg.maxGuardiansQuorumDelay <= MAX_DELAY_DURATION,
            ERROR_MAX_GUARDIANS_QUORUM_DELAY_EXCEEDED
        );
        require(cfg.minActivationAmount != 0, ERROR_ZERO_MIN_ACTIVATION_AMOUNT);
        require(cfg.maxDelayInflow != 0, ERROR_ZERO_MAX_DELAY_INFLOW);
        require(cfg.minDepositAmount <= cfg.minActivationAmount, ERROR_INVALID_MIN_DEPOSIT_AMOUNT);
        require(cfg.delayPerStrike <= MAX_DELAY_DURATION, ERROR_MAX_DELAY_PER_STRIKE_EXCEEDED);
        require(cfg.delayPerSuspect <= MAX_DELAY_DURATION, ERROR_MAX_DELAY_PER_SUSPECT_EXCEEDED);
    }
}
