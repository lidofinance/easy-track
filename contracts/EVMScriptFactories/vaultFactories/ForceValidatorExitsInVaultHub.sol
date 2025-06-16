// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IStakingVault.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to force validator exits for multiple vaults in VaultHub
contract ForceValidatorExitsInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_VAULT_HUB = "ZERO_VAULT_HUB";
    string private constant ERROR_ZERO_EVM_SCRIPT_EXECUTOR = "ZERO_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_EMPTY_PUBKEYS = "EMPTY_PUBKEYS";
    string private constant ERROR_INVALID_PUBKEYS_LENGTH = "INVALID_PUBKEYS_LENGTH";
    string private constant ERROR_NOT_ENOUGH_ETH = "NOT_ENOUGH_ETH";
    string private constant ERROR_WITHDRAWAL_FEE_READ_FAILED = "WITHDRAWAL_FEE_READ_FAILED";
    string private constant ERROR_WITHDRAWAL_FEE_INVALID_DATA = "WITHDRAWAL_FEE_INVALID_DATA";
    string private constant ERROR_ONLY_EVM_SCRIPT_EXECUTOR = "ONLY_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_NO_ETH_TO_WITHDRAW = "NO_ETH_TO_WITHDRAW";
    string private constant ERROR_ETH_TRANSFER_FAILED = "ETH_TRANSFER_FAILED";
    string private constant ERROR_OUT_OF_GAS = "OUT_OF_GAS";

    // -------------
    // VARIABLES
    // -------------

    address constant WITHDRAWAL_REQUEST = 0x00000961Ef480Eb55e80D19ad83579A64c007002;
    /// @notice The length of the public key in bytes
    uint256 private constant PUBLIC_KEY_LENGTH = 48;

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    /// @notice Address of EVMScriptExecutor
    address public immutable evmScriptExecutor;

    // -------------
    // EVENTS
    // -------------

    event ForceValidatorExitFailed(address indexed vault, bytes pubkeys);
    event LowBalance(uint256 value, uint256 balance);

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

    /// @notice Creates EVMScript to force validator exits for multiple vaults in VaultHub
    /// @param _creator Address who creates EVMScript and will receive refunds
    /// @param _evmScriptCallData Encoded: address[] _vaults, bytes[] _pubkeys
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory _vaults,
            bytes[] memory _pubkeys
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vaults, _pubkeys);

        address toAddress = address(this);
        bytes4 methodId = this.forceValidatorExit.selector;
        bytes[] memory calldataArray = new bytes[](_vaults.length);

        for (uint256 i = 0; i < _vaults.length; i++) {
            calldataArray[i] = abi.encode(
                _vaults[i],
                _pubkeys[i]
            );
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _vaults, bytes[] _pubkeys
    /// @return Vault addresses and validator pubkeys
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, bytes[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, bytes[] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], bytes[]));
    }

    function _validateInputData(
        address[] memory _vaults,
        bytes[] memory _pubkeys
    ) private view {
        require(_vaults.length > 0, ERROR_EMPTY_VAULTS);
        require(_vaults.length == _pubkeys.length, ERROR_ARRAY_LENGTH_MISMATCH);

        uint256 numKeys;
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), ERROR_ZERO_VAULT);
            require(_pubkeys[i].length > 0, ERROR_EMPTY_PUBKEYS);
            require(_pubkeys[i].length % PUBLIC_KEY_LENGTH == 0, ERROR_INVALID_PUBKEYS_LENGTH);
            numKeys += _pubkeys[i].length / PUBLIC_KEY_LENGTH;
        }

        // check if we have enough balance to pay for the validator exits
        uint256 value = numKeys * _getWithdrawalRequestFee();
        require(value <= address(this).balance, ERROR_NOT_ENOUGH_ETH);
    }

    /// @dev Retrieves the current EIP-7002 withdrawal fee.
    /// @return The minimum fee required per withdrawal request.
    function _getWithdrawalRequestFee() internal view returns (uint256) {
        (bool success, bytes memory feeData) = WITHDRAWAL_REQUEST.staticcall("");

        require(success, ERROR_WITHDRAWAL_FEE_READ_FAILED);
        require(feeData.length == 32, ERROR_WITHDRAWAL_FEE_INVALID_DATA);

        return abi.decode(feeData, (uint256));
    }

    // -------------
    // ADAPTER METHODS
    // -------------

    /// @notice Function to force validator exits in VaultHub
    /// @param _vault Address of the vault to exit validators from
    /// @param _pubkeys Public keys of the validators to exit
    function forceValidatorExit(
        address _vault,
        bytes calldata _pubkeys
    ) external payable {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        uint256 numKeys = _pubkeys.length / PUBLIC_KEY_LENGTH;
        uint256 value = IStakingVault(_vault).calculateValidatorWithdrawalFee(numKeys);
        if (value > address(this).balance) {
            emit LowBalance(value, address(this).balance);
            return;
        }

        try vaultHub.forceValidatorExit{value: value}(_vault, _pubkeys, address(this)) { // reverts if vault is disconnected or healthy
        } catch (bytes memory lowLevelRevertData) {
            /// @dev This check is required to prevent incorrect gas estimation of the method.
            ///      Without it, Ethereum nodes that use binary search for gas estimation may
            ///      return an invalid value when the forceValidatorExit() reverts because of the
            ///      "out of gas" error.
            ///      Here we assume that the forceValidatorExit() method doesn't have reverts with
            ///      empty error data except "out of gas".
            require(lowLevelRevertData.length != 0, ERROR_OUT_OF_GAS);
            emit ForceValidatorExitFailed(_vault, _pubkeys);
        }
    }

    /// @notice Function to withdraw all ETH to TrustedCaller
    function withdrawETH() external onlyTrustedCaller(msg.sender) {
        uint256 balance = address(this).balance;
        require(balance > 0, ERROR_NO_ETH_TO_WITHDRAW);

        (bool success, ) = msg.sender.call{value: balance}("");
        require(success, ERROR_ETH_TRANSFER_FAILED);
    }

    receive() external payable {}
}
