// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to update fees for multiple vaults in VaultHub
contract DecreaseVaultsFeesInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_VAULT_HUB = "ZERO_VAULT_HUB";
    string private constant ERROR_ZERO_EVM_SCRIPT_EXECUTOR = "ZERO_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_INFRA_FEE_TOO_HIGH = "INFRA_FEE_TOO_HIGH";
    string private constant ERROR_LIQUIDITY_FEE_TOO_HIGH = "LIQUIDITY_FEE_TOO_HIGH";
    string private constant ERROR_RESERVATION_FEE_TOO_HIGH = "RESERVATION_FEE_TOO_HIGH";
    string private constant ERROR_ONLY_EVM_SCRIPT_EXECUTOR = "ONLY_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_OUT_OF_GAS = "OUT_OF_GAS";

    // -------------
    // CONSTANTS
    // -------------

    /// @dev max value for fees in basis points - it's about 650%
    uint256 internal constant MAX_FEE_BP = type(uint16).max;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    /// @notice Address of EVMScriptExecutor
    address public immutable evmScriptExecutor;

    // -------------
    // EVENTS
    // -------------

    event VaultFeesUpdateFailed(address indexed vault, uint256 infraFeeBP, uint256 liquidityFeeBP, uint256 reservationFeeBP);

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

    /// @notice Creates EVMScript to update fees for multiple vaults in VaultHub
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _infraFeesBP, uint256[] _liquidityFeesBP, uint256[] _reservationFeesBP
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory _vaults,
            uint256[] memory _infraFeesBP,
            uint256[] memory _liquidityFeesBP,
            uint256[] memory _reservationFeesBP
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vaults, _infraFeesBP, _liquidityFeesBP, _reservationFeesBP);

        address toAddress = address(this);
        bytes4 methodId = this.updateVaultFees.selector;
        bytes[] memory calldataArray = new bytes[](_vaults.length);

        for (uint256 i = 0; i < _vaults.length; i++) {
            calldataArray[i] = abi.encode(
                _vaults[i],
                _infraFeesBP[i],
                _liquidityFeesBP[i],
                _reservationFeesBP[i]
            );
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _infraFeesBP, uint256[] _liquidityFeesBP, uint256[] _reservationFeesBP
    /// @return Vault addresses and new fee values in basis points
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, uint256[] memory, uint256[] memory, uint256[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, uint256[] memory, uint256[] memory, uint256[] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[], uint256[], uint256[]));
    }

    function _validateInputData(
        address[] memory _vaults,
        uint256[] memory _infraFeesBP,
        uint256[] memory _liquidityFeesBP,
        uint256[] memory _reservationFeesBP
    ) private pure {
        require(_vaults.length > 0, ERROR_EMPTY_VAULTS);
        require(
            _vaults.length == _infraFeesBP.length &&
            _vaults.length == _liquidityFeesBP.length &&
            _vaults.length == _reservationFeesBP.length,
            ERROR_ARRAY_LENGTH_MISMATCH
        );
        
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), ERROR_ZERO_VAULT);
            require(_infraFeesBP[i] <= MAX_FEE_BP, ERROR_INFRA_FEE_TOO_HIGH);
            require(_liquidityFeesBP[i] <= MAX_FEE_BP, ERROR_LIQUIDITY_FEE_TOO_HIGH);
            require(_reservationFeesBP[i] <= MAX_FEE_BP, ERROR_RESERVATION_FEE_TOO_HIGH);
            // more checks in adapter function to prevent motion failure in case vault disconnected while motion is in progress
        }
    }

    // -------------
    // ADAPTER METHODS
    // -------------

    /// @notice Function to update vault fees in VaultHub
    /// @param _vault Address of the vault to update fees for
    /// @param _infraFeeBP New infra fee in basis points
    /// @param _liquidityFeeBP New liquidity fee in basis points
    /// @param _reservationFeeBP New reservation fee in basis points
    function updateVaultFees(
        address _vault,
        uint256 _infraFeeBP,
        uint256 _liquidityFeeBP,
        uint256 _reservationFeeBP
    ) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        IVaultHub.VaultConnection memory connection = vaultHub.vaultConnection(_vault);
        if (_infraFeeBP > connection.infraFeeBP ||
            _liquidityFeeBP > connection.liquidityFeeBP ||
            _reservationFeeBP > connection.reservationFeeBP) {
            emit VaultFeesUpdateFailed(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
            return;
        }

        try vaultHub.updateVaultFees( // reverts if vault is disconnected while motion is in progress
            _vault,
            _infraFeeBP,
            _liquidityFeeBP,
            _reservationFeeBP
        ) {} catch (bytes memory lowLevelRevertData) {
            /// @dev This check is required to prevent incorrect gas estimation of the method.
            ///      Without it, Ethereum nodes that use binary search for gas estimation may
            ///      return an invalid value when the updateVaultFees() reverts because of the
            ///      "out of gas" error.
            ///      Here we assume that the updateVaultFees() method doesn't have reverts with
            ///      empty error data except "out of gas".
            require(lowLevelRevertData.length != 0, ERROR_OUT_OF_GAS);
            emit VaultFeesUpdateFailed(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
        }
    }
}
