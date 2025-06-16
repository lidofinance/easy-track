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
    // ERRORS
    // -------------

    error OutOfGasError();

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _vaultHub, address _evmScriptExecutor)
        TrustedCaller(_trustedCaller)
    {
        require(_vaultHub != address(0), "Zero VaultHub address");
        require(_evmScriptExecutor != address(0), "Zero EVMScriptExecutor address");

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
        require(_badDebtVaults.length > 0, "Empty bad debt vaults array");
        require(_badDebtVaults.length == _vaultAcceptors.length, "Array length mismatch");
        require(_badDebtVaults.length == _maxSharesToSocialize.length, "Array length mismatch");
        
        for (uint256 i = 0; i < _badDebtVaults.length; i++) {
            require(_badDebtVaults[i] != address(0), "Zero bad debt vault address");
            // acceptor address can't be zero - as it means to socialize bad debt to the core protocol
            require(_vaultAcceptors[i] != address(0), "Zero vault acceptor address");
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
        require(msg.sender == evmScriptExecutor, "Only EVMScriptExecutor");

        try vaultHub.socializeBadDebt(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize) { // reverts if vault is disconnected while motion is in progress
        } catch (bytes memory lowLevelRevertData) {
            /// @dev This check is required to prevent incorrect gas estimation of the method.
            ///      Without it, Ethereum nodes that use binary search for gas estimation may
            ///      return an invalid value when the socializeBadDebt() reverts because of the
            ///      "out of gas" error.
            ///      Here we assume that the socializeBadDebt() method doesn't have reverts with
            ///      empty error data except "out of gas".
            if (lowLevelRevertData.length == 0) revert OutOfGasError();
            emit BadDebtSocializationFailed(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize);
        }
    }
} 
