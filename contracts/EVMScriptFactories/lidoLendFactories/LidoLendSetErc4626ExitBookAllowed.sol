// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to set vaults' allow-list state on Erc4626ExitBook
contract LidoLendSetErc4626ExitBookAllowed is TrustedCaller, IEVMScriptFactory {
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";

    /// @notice Address of the domain's Erc4626ExitBook
    address public immutable erc4626ExitBook;

    constructor(address _trustedCaller, address _erc4626ExitBook) TrustedCaller(_trustedCaller) {
        erc4626ExitBook = _erc4626ExitBook;
    }

    /// @notice Creates EVMScript to set vaults' allow-list state on Erc4626ExitBook
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address[] vaults, bool allowed)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory vaults, bool allowed) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(vaults.length > 0, ERROR_EMPTY_VAULTS);

        bytes[] memory encodedCalldata = new bytes[](vaults.length);

        for (uint256 i = 0; i < vaults.length; ++i) {
            require(vaults[i] != address(0), ERROR_ZERO_VAULT);
            encodedCalldata[i] = abi.encode(vaults[i], allowed);
        }

        return
            EVMScriptCreator.createEVMScript(
                erc4626ExitBook,
                IErc4626ExitBook.setVaultAllowed.selector,
                encodedCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address[] vaults, bool allowed)
    /// @return vaults Vault addresses whose allow-list state is set
    /// @return allowed Target allow-list state
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address[] memory vaults, bool allowed)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory vaults, bool allowed)
    {
        (vaults, allowed) = abi.decode(_evmScriptCallData, (address[], bool));
    }
}
