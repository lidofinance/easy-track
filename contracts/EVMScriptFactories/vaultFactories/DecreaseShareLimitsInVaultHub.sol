// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultHubAdapter.sol";

/// @author dry914
/// @notice Creates EVMScript to update share limits for multiple vaults in VaultHub
contract DecreaseShareLimitsInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_ADAPTER = "ZERO_ADAPTER";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub adapter
    IVaultHubAdapter public immutable vaultHubAdapter;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _adapter)
        TrustedCaller(_trustedCaller)
    {   
        require(_adapter != address(0), ERROR_ZERO_ADAPTER);
        vaultHubAdapter = IVaultHubAdapter(_adapter);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to update share limits for multiple vaults in VaultHub
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _shareLimits
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory _vaults, uint256[] memory _shareLimits) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vaults, _shareLimits);

        address toAddress = address(vaultHubAdapter);
        bytes4 methodId = vaultHubAdapter.updateShareLimit.selector;
        bytes[] memory calldataArray = new bytes[](_vaults.length);

        for (uint256 i = 0; i < _vaults.length; i++) {
            calldataArray[i] = abi.encode(_vaults[i], _shareLimits[i]);
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _shareLimits
    /// @return Vault addresses and new share limit values
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
        uint256[] memory _shareLimits
    ) private pure {
        require(_vaults.length > 0, ERROR_EMPTY_VAULTS);
        require(_vaults.length == _shareLimits.length, ERROR_ARRAY_LENGTH_MISMATCH);
        
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), ERROR_ZERO_VAULT);
            // shareLimit check in adapter to prevent motion failure in case vault disconnected while motion is in progress
        }
    }
}
