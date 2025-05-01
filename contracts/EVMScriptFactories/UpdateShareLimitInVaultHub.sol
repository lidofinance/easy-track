// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to update share limit for a vault in VaultHub
contract UpdateShareLimitInVaultHub is TrustedCaller, IEVMScriptFactory {

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

    /// @notice Creates EVMScript to update share limit for a vault in VaultHub
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address _vault, uint256 _shareLimit
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address _vault, uint256 _shareLimit) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vault, _shareLimit);

        return
            EVMScriptCreator.createEVMScript(
                address(vaultHub),
                IVaultHub.updateShareLimit.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address _vault, uint256 _shareLimit
    /// @return Vault address and new share limit value
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address, uint256)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address, uint256)
    {
        return abi.decode(_evmScriptCallData, (address, uint256));
    }

    function _validateInputData(
        address _vault,
        uint256 _shareLimit
    ) private view {
        require(_vault != address(0), "Zero vault address");
        
        IVaultHub.VaultSocket memory socket = vaultHub.vaultSocket(_vault);
        require(socket.vault != address(0), "Vault not registered");
    }
} 