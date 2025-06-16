// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to socialize bad debt for multiple vaults in VaultHub
contract SocializeBadDebtInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_VAULT_HUB = "ZERO_VAULT_HUB";
    string private constant ERROR_ZERO_EVM_SCRIPT_EXECUTOR = "ZERO_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_EMPTY_BAD_DEBT_VAULTS = "EMPTY_BAD_DEBT_VAULTS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_BAD_DEBT_VAULT = "ZERO_BAD_DEBT_VAULT";
    string private constant ERROR_ZERO_VAULT_ACCEPTOR = "ZERO_VAULT_ACCEPTOR";
    string private constant ERROR_ONLY_EVM_SCRIPT_EXECUTOR = "ONLY_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_OUT_OF_GAS = "OUT_OF_GAS";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    /// @notice Address of the EVMScriptExecutor
    address public immutable evmScriptExecutor;

    // -------------
    // EVENTS
    // -------------

    event BadDebtSocializationFailed(address indexed badDebtVault, address indexed vaultAcceptor, uint256 maxSharesToSocialize);

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

        address toAddress = address(this);
        bytes4 methodId = this.socializeBadDebt.selector;
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
        require(_badDebtVaults.length > 0, ERROR_EMPTY_BAD_DEBT_VAULTS);
        require(
            _badDebtVaults.length == _vaultAcceptors.length &&
            _badDebtVaults.length == _maxSharesToSocialize.length,
            ERROR_ARRAY_LENGTH_MISMATCH
        );
        
        for (uint256 i = 0; i < _badDebtVaults.length; i++) {
            require(_badDebtVaults[i] != address(0), ERROR_ZERO_BAD_DEBT_VAULT);
            // acceptor address can't be zero - as it means to socialize bad debt to the core protocol
            require(_vaultAcceptors[i] != address(0), ERROR_ZERO_VAULT_ACCEPTOR);
        }
    }

    // -------------
    // ADAPTER METHODS
    // -------------

    /// @notice Socializes bad debt for a vault
    /// @param _badDebtVault address of the vault that has the bad debt
    /// @param _vaultAcceptor address of the vault that will accept the bad debt or 0 if the bad debt is internalized to the protocol
    /// @param _maxSharesToSocialize maximum amount of shares to socialize
    function socializeBadDebt(
        address _badDebtVault,
        address _vaultAcceptor,
        uint256 _maxSharesToSocialize
    ) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        try vaultHub.socializeBadDebt(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize) { // reverts if vault is disconnected while motion is in progress
        } catch (bytes memory lowLevelRevertData) {
            /// @dev This check is required to prevent incorrect gas estimation of the method.
            ///      Without it, Ethereum nodes that use binary search for gas estimation may
            ///      return an invalid value when the socializeBadDebt() reverts because of the
            ///      "out of gas" error.
            ///      Here we assume that the socializeBadDebt() method doesn't have reverts with
            ///      empty error data except "out of gas".
            require(lowLevelRevertData.length != 0, ERROR_OUT_OF_GAS);
            emit BadDebtSocializationFailed(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize);
        }
    }
} 
