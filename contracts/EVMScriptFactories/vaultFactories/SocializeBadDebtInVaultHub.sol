// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../adapters/SocializeBadDebtAdapter.sol";

/// @author dry914
/// @notice Creates EVMScript to socialize bad debt for multiple vaults in VaultHub
contract SocializeBadDebtInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub adapter
    SocializeBadDebtAdapter public immutable adapter;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address payable _adapter)
        TrustedCaller(_trustedCaller)
    {
        require(_adapter != address(0), "Zero adapter");

        adapter = SocializeBadDebtAdapter(_adapter);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to socialize bad debt for multiple vaults in VaultHub
    /// @param _creator Address who creates EVMScript and will receive refunds
    /// @param _evmScriptCallData Encoded: address[] _badDebtVaults, address[] _vaultAcceptors, uint256[] _maxSharesToSocialize
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory _badDebtVaults,
            address[] memory _vaultAcceptors,
            uint256[] memory _maxSharesToSocialize
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_badDebtVaults, _vaultAcceptors, _maxSharesToSocialize);

        address toAddress = address(adapter);
        bytes4 methodId = SocializeBadDebtAdapter.socializeBadDebt.selector;
        bytes[] memory calldataArray = new bytes[](_badDebtVaults.length);

        for (uint256 i = 0; i < _badDebtVaults.length; i++) {
            calldataArray[i] = abi.encode(
                _badDebtVaults[i],
                _vaultAcceptors[i],
                _maxSharesToSocialize[i]
            );
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _badDebtVaults, address[] _vaultAcceptors, uint256[] _maxSharesToSocialize
    /// @return Bad debt vault addresses, vault acceptor addresses, and max shares to socialize
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, address[] memory, uint256[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, address[] memory, uint256[] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], address[], uint256[]));
    }

    function _validateInputData(
        address[] memory _badDebtVaults,
        address[] memory _vaultAcceptors,
        uint256[] memory _maxSharesToSocialize
    ) private pure {
        require(_badDebtVaults.length > 0, "Empty bad debt vaults array");
        require(_badDebtVaults.length == _vaultAcceptors.length, "Array length mismatch");
        require(_badDebtVaults.length == _maxSharesToSocialize.length, "Array length mismatch");
        
        for (uint256 i = 0; i < _badDebtVaults.length; i++) {
            require(_badDebtVaults[i] != address(0), "Zero bad debt vault address");
            // acceptor address can't be zero - as it means to socialize bad debt to the core protocol
            require(_vaultAcceptors[i] != address(0), "Zero vault acceptor address");
        }
    }
} 
