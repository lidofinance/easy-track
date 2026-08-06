// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to set a Lido Lend market's allow-list state on MorphoExitBook
contract LidoLendSetMorphoExitBookAllowed is TrustedCaller, IEVMScriptFactory {
    /// @notice Address of the domain's MorphoExitBook
    address public immutable morphoExitBook;

    constructor(address _trustedCaller, address _morphoExitBook) TrustedCaller(_trustedCaller) {
        morphoExitBook = _morphoExitBook;
    }

    /// @notice Creates EVMScript to set a market's allow-list state on MorphoExitBook
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (MarketParams marketParams, bool allowed)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        _decodeEVMScriptCallData(_evmScriptCallData);
        return
            EVMScriptCreator.createEVMScript(
                morphoExitBook,
                IMorphoExitBook.setMarketAllowed.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (MarketParams memory marketParams, bool allowed)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (MarketParams memory marketParams, bool allowed)
    {
        (marketParams, allowed) = abi.decode(_evmScriptCallData, (MarketParams, bool));
    }
}
