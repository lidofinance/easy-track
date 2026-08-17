// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to unfreeze one or more Lido Lend markets
contract LidoLendUnfreezeMarket is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_MARKET_IS_NOT_FROZEN = "MARKET_IS_NOT_FROZEN";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to unfreeze one or more Lido Lend markets
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32[] marketIds)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        bytes32[] memory marketIds = _decodeEVMScriptCallData(_evmScriptCallData);
        require(marketIds.length > 0, ERROR_EMPTY_MARKETS_LIST);

        bytes[] memory encodedCalldata = new bytes[](marketIds.length);
        for (uint256 i = 0; i < marketIds.length; ++i) {
            require(_controllerOf(marketIds[i]).isFrozen(), ERROR_MARKET_IS_NOT_FROZEN);
            encodedCalldata[i] = abi.encode(marketIds[i]);
        }

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.unfreezeMarket.selector,
                encodedCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32[] marketIds)
    /// @return Ids of the markets to unfreeze
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32[] memory marketIds)
    {
        (marketIds) = abi.decode(_evmScriptCallData, (bytes32[]));
    }
}
