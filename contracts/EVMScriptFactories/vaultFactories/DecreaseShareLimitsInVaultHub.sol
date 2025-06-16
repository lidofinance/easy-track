// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to update share limits for multiple vaults in VaultHub
contract DecreaseShareLimitsInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_VAULT_HUB = "ZERO_VAULT_HUB";
    string private constant ERROR_ZERO_EVM_SCRIPT_EXECUTOR = "ZERO_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_ONLY_EVM_SCRIPT_EXECUTOR = "ONLY_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_OUT_OF_GAS = "OUT_OF_GAS";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the EVMScriptExecutor
    address public immutable evmScriptExecutor;

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    // -------------
    // EVENTS
    // -------------

    event ShareLimitUpdateFailed(address indexed vault, uint256 shareLimit);

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _vaultHub, address _evmScriptExecutor)
        TrustedCaller(_trustedCaller)
    {   
        require(_vaultHub != address(0), ERROR_ZERO_VAULT_HUB);
        require(_evmScriptExecutor != address(0), ERROR_ZERO_EVM_SCRIPT_EXECUTOR);

        vaultHub = IVaultHub(_vaultHub);
        evmScriptExecutor = _evmScriptExecutor;
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

        address toAddress = address(this);
        bytes4 methodId = this.updateShareLimit.selector;
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

    // -------------
    // ADAPTER METHODS
    // -------------

    /// @notice Updates share limit for a vault
    /// @param _vault address of the vault to update
    /// @param _shareLimit new share limit value
    function updateShareLimit(address _vault, uint256 _shareLimit) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        if (_shareLimit > vaultHub.vaultConnection(_vault).shareLimit) {
            emit ShareLimitUpdateFailed(_vault, _shareLimit);
            return;
        }

        try vaultHub.updateShareLimit(_vault, _shareLimit) { // reverts if vault is disconnected while motion is in progress
        } catch (bytes memory lowLevelRevertData) {
            /// @dev This check is required to prevent incorrect gas estimation of the method.
            ///      Without it, Ethereum nodes that use binary search for gas estimation may
            ///      return an invalid value when the updateShareLimit() reverts because of the
            ///      "out of gas" error.
            ///      Here we assume that the updateShareLimit() method doesn't have reverts with
            ///      empty error data except "out of gas".
            require(lowLevelRevertData.length != 0, ERROR_OUT_OF_GAS);
            emit ShareLimitUpdateFailed(_vault, _shareLimit);
        }
    }
}
