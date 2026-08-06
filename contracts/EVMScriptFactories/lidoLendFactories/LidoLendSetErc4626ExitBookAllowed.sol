// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to set a vault's allow-list state on Erc4626ExitBook
contract LidoLendSetErc4626ExitBookAllowed is TrustedCaller, IEVMScriptFactory {
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";

    /// @notice Address of the domain's Erc4626ExitBook
    address public immutable erc4626ExitBook;

    constructor(address _trustedCaller, address _erc4626ExitBook) TrustedCaller(_trustedCaller) {
        erc4626ExitBook = _erc4626ExitBook;
    }

    /// @notice Creates EVMScript to set a vault's allow-list state on Erc4626ExitBook
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address vault, bool allowed)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address vault, ) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(vault != address(0), ERROR_ZERO_VAULT);

        return
            EVMScriptCreator.createEVMScript(
                erc4626ExitBook,
                IErc4626ExitBook.setVaultAllowed.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address vault, bool allowed)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address vault, bool allowed)
    {
        (vault, allowed) = abi.decode(_evmScriptCallData, (address, bool));
    }
}
