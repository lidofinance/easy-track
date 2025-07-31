// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultHubAdapter.sol";

/// @author dry914
/// @notice Creates EVMScript to force validator exits for multiple vaults in VaultHub
contract ForceValidatorExitsInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_ADAPTER = "ZERO_ADAPTER";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_EMPTY_PUBKEYS = "EMPTY_PUBKEYS";
    string private constant ERROR_INVALID_PUBKEYS_LENGTH = "INVALID_PUBKEYS_LENGTH";
    string private constant ERROR_NOT_ENOUGH_ETH = "NOT_ENOUGH_ETH";
    string private constant ERROR_WITHDRAWAL_FEE_READ_FAILED = "WITHDRAWAL_FEE_READ_FAILED";
    string private constant ERROR_WITHDRAWAL_FEE_INVALID_DATA = "WITHDRAWAL_FEE_INVALID_DATA";
    string private constant ERROR_VALIDATOR_EXIT_FEE_LIMIT_EXCEEDED = "VALIDATOR_EXIT_FEE_LIMIT_EXCEEDED";

    // -------------
    // VARIABLES
    // -------------

    address public constant WITHDRAWAL_REQUEST_PREDEPLOY_ADDRESS = 0x00000961Ef480Eb55e80D19ad83579A64c007002;
    /// @notice The length of the public key in bytes
    uint256 private constant PUBLIC_KEY_LENGTH = 48;

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

    /// @notice Creates EVMScript to force validator exits for multiple vaults in VaultHub
    /// @param _creator Address who creates EVMScript
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

        address toAddress = address(vaultHubAdapter);
        bytes4 methodId = vaultHubAdapter.forceValidatorExit.selector;
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

        // check if the validator exit fee limit is exceeded
        uint256 fee = _getWithdrawalRequestFee();
        require(fee <= vaultHubAdapter.validatorExitFeeLimit(), ERROR_VALIDATOR_EXIT_FEE_LIMIT_EXCEEDED);
        // check if we have enough balance to pay for the validator exits
        require(numKeys * fee <= address(vaultHubAdapter).balance, ERROR_NOT_ENOUGH_ETH);
    }

    /// @dev Retrieves the current EIP-7002 withdrawal fee.
    /// @return The minimum fee required per withdrawal request.
    function _getWithdrawalRequestFee() internal view returns (uint256) {
        (bool success, bytes memory feeData) = WITHDRAWAL_REQUEST_PREDEPLOY_ADDRESS.staticcall("");

        require(success, ERROR_WITHDRAWAL_FEE_READ_FAILED);
        require(feeData.length == 32, ERROR_WITHDRAWAL_FEE_INVALID_DATA);

        return abi.decode(feeData, (uint256));
    }
}
