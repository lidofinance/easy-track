// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to update share limits for multiple vaults in VaultHub
contract UpdateShareLimitsInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _vaultHub)
        TrustedCaller(_trustedCaller)
    {
        vaultHub = IVaultHub(_vaultHub);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to update share limits for multiple vaults in VaultHub
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _shareLimits
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory _vaults, uint256[] memory _shareLimits) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vaults, _shareLimits);

        return
            EVMScriptCreator.createEVMScript(
                address(vaultHub),
                IVaultHub.updateShareLimits.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _shareLimits
    /// @return Vault addresses and new share limit values
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address[] memory, uint256[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, uint256[] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[]));
    }

    function _validateInputData(
        address[] memory _vaults,
        uint256[] memory _shareLimits
    ) private view {
        require(_vaults.length > 0, "Empty vaults array");
        require(_vaults.length == _shareLimits.length, "Array length mismatch");
        
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), "Zero vault address");
            
            IVaultHub.VaultSocket memory socket = vaultHub.vaultSocket(_vaults[i]);
            require(socket.vault != address(0), "Vault not registered");
        }
    }
} 