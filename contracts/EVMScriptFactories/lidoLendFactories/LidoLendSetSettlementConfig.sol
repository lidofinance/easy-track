// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to update the settlement config of one Lido Lend market
contract LidoLendSetSettlementConfig is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_SAME_CONFIG = "SAME_CONFIG";
    string private constant ERROR_CONFIG_OUT_OF_RANGE = "SETTLEMENT_CONFIG_OUT_OF_RANGE";

    uint256 private constant BPS = 10_000;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to update the settlement config of one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, SettlementConfig config)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            bytes32 marketId,
            ILidoLendMarketController.SettlementConfig memory newConfig
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        ILidoLendMarketController marketController = _controllerOf(marketId);

        require(
            newConfig.sliceFloorBps <= BPS && newConfig.ltvStepBps <= BPS,
            ERROR_CONFIG_OUT_OF_RANGE
        );
        require(
            keccak256(abi.encode(newConfig)) !=
                keccak256(abi.encode(marketController.settlementConfig())),
            ERROR_SAME_CONFIG
        );

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setMarketSettlementConfig.selector,
                abi.encode(marketId, newConfig)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, SettlementConfig config)
    /// @return marketId Id of the market
    /// @return config Decoded settlement config
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, ILidoLendMarketController.SettlementConfig memory config)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, ILidoLendMarketController.SettlementConfig memory config)
    {
        (marketId, config) = abi.decode(
            _evmScriptCallData,
            (bytes32, ILidoLendMarketController.SettlementConfig)
        );
    }
}
