// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to unban accounts on one or more Lido Lend markets
contract LidoLendUnbanAccount is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to unban accounts on one or more Lido Lend markets
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32[] marketIds, address[] accounts)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32[] memory marketIds, address[] memory accounts) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        require(marketIds.length > 0, ERROR_EMPTY_MARKETS_LIST);
        require(marketIds.length == accounts.length, ERROR_ARRAY_LENGTH_MISMATCH);

        bytes[] memory encodedCalldata = new bytes[](marketIds.length);
        bytes32[] memory singleMarket = new bytes32[](1);
        for (uint256 i = 0; i < marketIds.length; ++i) {
            _guardianSignalsOf(marketIds[i]);
            singleMarket[0] = marketIds[i];
            encodedCalldata[i] = abi.encode(singleMarket, accounts[i]);
        }

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.unbanGuardianSignals.selector,
                encodedCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (bytes32[] marketIds, address[] accounts)
    /// @return marketIds Ids of the markets
    /// @return accounts Addresses to unban
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32[] memory marketIds, address[] memory accounts)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32[] memory marketIds, address[] memory accounts)
    {
        (marketIds, accounts) = abi.decode(_evmScriptCallData, (bytes32[], address[]));
    }
}
