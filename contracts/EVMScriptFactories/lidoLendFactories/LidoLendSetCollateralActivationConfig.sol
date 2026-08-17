// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to update the collateral-activation config of one Lido Lend market
contract LidoLendSetCollateralActivationConfig is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

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
    string private constant ERROR_MAX_DELAY_PER_STRIKE_EXCEEDED = "MAX_DELAY_PER_STRIKE_EXCEEDED";
    string private constant ERROR_MAX_DELAY_PER_SUSPECT_EXCEEDED = "MAX_DELAY_PER_SUSPECT_EXCEEDED";

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

    /// @notice Creates EVMScript to update the collateral-activation config of one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, CollateralActivationConfig cfg)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            bytes32 marketId,
            ILidoLendMarketController.CollateralActivationConfig memory newCfg
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        ILidoLendMarketController marketController = _controllerOf(marketId);

        _validateConfig(newCfg);
        require(
            keccak256(abi.encode(newCfg)) !=
                keccak256(abi.encode(marketController.collateralActivationConfig())),
            ERROR_SAME_CONFIG
        );

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setMarketCollateralActivationConfig.selector,
                abi.encode(marketId, newCfg)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, CollateralActivationConfig cfg)
    /// @return marketId Id of the market
    /// @return cfg Decoded collateral-activation config
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, ILidoLendMarketController.CollateralActivationConfig memory cfg)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _validateConfig(ILidoLendMarketController.CollateralActivationConfig memory cfg)
        private
        pure
    {
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
        require(cfg.delayPerStrike <= MAX_DELAY_DURATION, ERROR_MAX_DELAY_PER_STRIKE_EXCEEDED);
        require(cfg.delayPerSuspect <= MAX_DELAY_DURATION, ERROR_MAX_DELAY_PER_SUSPECT_EXCEEDED);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, ILidoLendMarketController.CollateralActivationConfig memory cfg)
    {
        (marketId, cfg) = abi.decode(
            _evmScriptCallData,
            (bytes32, ILidoLendMarketController.CollateralActivationConfig)
        );
    }
}
