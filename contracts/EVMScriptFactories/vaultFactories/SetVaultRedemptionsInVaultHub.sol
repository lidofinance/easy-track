// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to set vault redemptions for multiple vaults in VaultHub
contract SetVaultRedemptionsInVaultHub is TrustedCaller, IEVMScriptFactory {

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

    /// @notice Creates EVMScript to set vault redemptions for multiple vaults in VaultHub
    /// @param _creator Address who creates EVMScript and will receive refunds
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _redemptionsValues
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory _vaults,
            uint256[] memory _redemptionsValues
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vaults, _redemptionsValues);

        address toAddress = address(vaultHub);
        bytes4 methodId = IVaultHub.setVaultRedemptions.selector;
        bytes[] memory calldataArray = new bytes[](_vaults.length);

        for (uint256 i = 0; i < _vaults.length; i++) {
            calldataArray[i] = abi.encode(
                _vaults[i],
                _redemptionsValues[i]
            );
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _redemptionsValues
    /// @return Vault addresses and redemptions values
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
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
        uint256[] memory _redemptionsValues
    ) private pure {
        require(_vaults.length > 0, "Empty vaults array");
        require(_vaults.length == _redemptionsValues.length, "Array length mismatch");
        
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), "Zero vault address");
        }
    }
} 
