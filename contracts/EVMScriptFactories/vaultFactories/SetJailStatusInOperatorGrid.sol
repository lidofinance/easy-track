// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultsAdapter.sol";

/// @author dry914
/// @notice Creates EVMScript to set jail status for multiple vaults in OperatorGrid
contract SetJailStatusInOperatorGrid is TrustedCaller, IEVMScriptFactory {

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

    /// @notice Address of Vaults adapter
    IVaultsAdapter public immutable vaultsAdapter;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _adapter)
        TrustedCaller(_trustedCaller)
    {
        require(_adapter != address(0), ERROR_ZERO_ADAPTER);
        vaultsAdapter = IVaultsAdapter(_adapter);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set jail status for multiple vaults in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address[] _vaults, bool[] _jailStatuses
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory _vaults, bool[] memory _jailStatuses) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vaults, _jailStatuses);

        address toAddress = address(vaultsAdapter);
        bytes4 methodId = vaultsAdapter.setVaultJailStatus.selector;
        bytes[] memory calldataArray = new bytes[](_vaults.length);

        for (uint256 i = 0; i < _vaults.length; i++) {
            calldataArray[i] = abi.encode(_vaults[i], _jailStatuses[i]);
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _vaults, bool[] _jailStatuses
    /// @return Vault addresses and jail statuses
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, bool[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, bool[] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], bool[]));
    }

    function _validateInputData(
        address[] memory _vaults,
        bool[] memory _jailStatuses
    ) private pure {
        require(_vaults.length > 0, ERROR_EMPTY_VAULTS);
        require(_vaults.length == _jailStatuses.length, ERROR_ARRAY_LENGTH_MISMATCH);

        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), ERROR_ZERO_VAULT);
        }
    }
}
