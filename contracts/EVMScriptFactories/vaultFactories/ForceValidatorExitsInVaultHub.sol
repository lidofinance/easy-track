// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../adapters/ForceValidatorExitAdapter.sol";
import "../../interfaces/IStakingVault.sol";

/// @author dry914
/// @notice Creates EVMScript to force validator exits for multiple vaults in VaultHub
contract ForceValidatorExitsInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // VARIABLES
    // -------------

    address constant WITHDRAWAL_REQUEST = 0x00000961Ef480Eb55e80D19ad83579A64c007002;
    /// @notice The length of the public key in bytes
    uint256 private constant PUBLIC_KEY_LENGTH = 48;

    /// @notice Address of VaultHub
    ForceValidatorExitAdapter public immutable adapter;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address payable _adapter)
        TrustedCaller(_trustedCaller)
    {
        require(_adapter != address(0), "Zero adapter");

        adapter = ForceValidatorExitAdapter(_adapter);
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

        address toAddress = address(adapter);
        bytes4 methodId = ForceValidatorExitAdapter.forceValidatorExit.selector;
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
        require(_vaults.length > 0, "Empty vaults array");
        require(_vaults.length == _pubkeys.length, "Array length mismatch");

        uint256 numKeys;
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), "Zero vault address");
            require(_pubkeys[i].length > 0, "Empty pubkeys");
            require(_pubkeys[i].length % PUBLIC_KEY_LENGTH == 0, "Invalid pubkeys length");
            numKeys += _pubkeys[i].length / PUBLIC_KEY_LENGTH;
        }

        // check if we have enough balance on the adapter to pay for the validator exits
        uint256 value = numKeys * _getWithdrawalRequestFee();
        require(value <= address(adapter).balance, "Not enough balance on the adapter");
    }

    /// @dev Retrieves the current EIP-7002 withdrawal fee.
    /// @return The minimum fee required per withdrawal request.
    function _getWithdrawalRequestFee() internal view returns (uint256) {
        (bool success, bytes memory feeData) = WITHDRAWAL_REQUEST.staticcall("");

        require(success, "Withdrawal fee read failed");
        require(feeData.length == 32, "Withdrawal fee invalid data");

        return abi.decode(feeData, (uint256));
    }
}
