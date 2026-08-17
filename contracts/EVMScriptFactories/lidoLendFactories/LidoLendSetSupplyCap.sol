// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to set the supply cap of one Lido Lend market
contract LidoLendSetSupplyCap is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set the supply cap of one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 cap)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newCap) = _decodeEVMScriptCallData(_evmScriptCallData);

        _controllerOf(marketId);

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setMarketSupplyCap.selector,
                abi.encode(marketId, newCap)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 cap)
    /// @return marketId Id of the market
    /// @return cap New supply cap
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, uint256 cap)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, uint256 cap)
    {
        (marketId, cap) = abi.decode(_evmScriptCallData, (bytes32, uint256));
    }
}
