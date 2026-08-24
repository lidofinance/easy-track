// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to set Lido Lend markets' allow-list state on MorphoExitBook
contract LidoLendSetMorphoExitBookAllowed is TrustedCaller, IEVMScriptFactory {
    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_ZERO_EXIT_BOOK = "ZERO_EXIT_BOOK";

    constructor(address _trustedCaller) TrustedCaller(_trustedCaller) {}

    /// @notice Creates EVMScript to set markets' allow-list state on MorphoExitBook
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address exitBook, MarketParams[] marketParams, bool allowed)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address exitBook,
            MarketParams[] memory marketParams,
            bool allowed
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(exitBook != address(0), ERROR_ZERO_EXIT_BOOK);
        require(marketParams.length > 0, ERROR_EMPTY_MARKETS_LIST);

        bytes[] memory encodedCalldata = new bytes[](marketParams.length);
        for (uint256 i = 0; i < marketParams.length; ++i) {
            encodedCalldata[i] = abi.encode(marketParams[i], allowed);
        }

        return
            EVMScriptCreator.createEVMScript(
                exitBook,
                IMorphoExitBook.setMarketAllowed.selector,
                encodedCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address exitBook, MarketParams[] marketParams, bool allowed)
    /// @return exitBook MorphoExitBook whose allow-list state is set
    /// @return marketParams Market params whose allow-list state is set
    /// @return allowed Target allow-list state
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            address exitBook,
            MarketParams[] memory marketParams,
            bool allowed
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            address exitBook,
            MarketParams[] memory marketParams,
            bool allowed
        )
    {
        (exitBook, marketParams, allowed) = abi.decode(
            _evmScriptCallData,
            (address, MarketParams[], bool)
        );
    }
}
