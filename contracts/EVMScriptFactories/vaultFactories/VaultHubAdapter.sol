// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Adapter for VaultHub to be used in EVMScriptFactories
contract VaultHubAdapter is TrustedCaller {
    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ONLY_EVM_SCRIPT_EXECUTOR = "ONLY_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_OUT_OF_GAS = "OUT_OF_GAS";
    string private constant ERROR_NOT_ENOUGH_ETH = "NOT_ENOUGH_ETH";
    string private constant ERROR_NO_ETH_TO_WITHDRAW = "NO_ETH_TO_WITHDRAW";
    string private constant ERROR_ETH_TRANSFER_FAILED = "ETH_TRANSFER_FAILED";
    string private constant ERROR_ZERO_VAULT_HUB = "ZERO_VAULT_HUB";
    string private constant ERROR_ZERO_EVM_SCRIPT_EXECUTOR = "ZERO_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_ZERO_VALIDATOR_EXIT_FEE_LIMIT = "ZERO_VALIDATOR_EXIT_FEE_LIMIT";
    string private constant ERROR_VALIDATOR_EXIT_FEE_LIMIT_EXCEEDED = "VALIDATOR_EXIT_FEE_LIMIT_EXCEEDED";
    string private constant ERROR_WITHDRAWAL_FEE_READ_FAILED = "WITHDRAWAL_FEE_READ_FAILED";
    string private constant ERROR_WITHDRAWAL_FEE_INVALID_DATA = "WITHDRAWAL_FEE_INVALID_DATA";

    // -------------
    // CONSTANTS
    // -------------
    
    uint256 private constant PUBLIC_KEY_LENGTH = 48;
    address public constant WITHDRAWAL_REQUEST_PREDEPLOY_ADDRESS = 0x00000961Ef480Eb55e80D19ad83579A64c007002;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    /// @notice Address of the EVMScriptExecutor
    address public immutable evmScriptExecutor;

    /// @notice Fee limit for validator exits
    uint256 public validatorExitFeeLimit;

    // -------------
    // EVENTS
    // -------------

    event ShareLimitUpdateFailed(address indexed vault, uint256 shareLimit);
    event VaultFeesUpdateFailed(address indexed vault, uint256 infraFeeBP, uint256 liquidityFeeBP, uint256 reservationFeeBP);
    event BadDebtSocializationFailed(address indexed badDebtVault, address indexed vaultAcceptor, uint256 maxSharesToSocialize);
    event ForceValidatorExitFailed(address indexed vault, bytes pubkeys);
    event WithdrawalRequestFeeUpdated(uint256 oldFee, uint256 newFee);

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _vaultHub, address _evmScriptExecutor, uint256 _validatorExitFeeLimit)
        TrustedCaller(_trustedCaller)
    {   
        require(_vaultHub != address(0), ERROR_ZERO_VAULT_HUB);
        require(_evmScriptExecutor != address(0), ERROR_ZERO_EVM_SCRIPT_EXECUTOR);
        require(_validatorExitFeeLimit > 0, ERROR_ZERO_VALIDATOR_EXIT_FEE_LIMIT);

        vaultHub = IVaultHub(_vaultHub);
        evmScriptExecutor = _evmScriptExecutor;
        validatorExitFeeLimit = _validatorExitFeeLimit;
    }

    // -------------
    // EXTERNAL METHODS
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
        if (connection.vaultIndex == 0 || // vault is not connected to hub
            connection.pendingDisconnect || // vault is disconnecting
            _infraFeeBP > connection.infraFeeBP ||
            _liquidityFeeBP > connection.liquidityFeeBP ||
            _reservationFeeBP > connection.reservationFeeBP) {
            emit VaultFeesUpdateFailed(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
            return;
        }

        vaultHub.updateVaultFees(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
    }

    /// @notice Updates share limit for a vault
    /// @param _vault address of the vault to update
    /// @param _shareLimit new share limit value
    function updateShareLimit(address _vault, uint256 _shareLimit) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        IVaultHub.VaultConnection memory connection = vaultHub.vaultConnection(_vault);
        if (connection.vaultIndex == 0 || // vault is not connected to hub
            connection.pendingDisconnect || // vault is disconnecting
            _shareLimit > connection.shareLimit) {
            emit ShareLimitUpdateFailed(_vault, _shareLimit);
            return;
        }

        vaultHub.updateShareLimit(_vault, _shareLimit);
    }

    /// @notice Socializes bad debt for a vault
    /// @param _badDebtVault address of the vault that has the bad debt
    /// @param _vaultAcceptor address of the vault that will accept the bad debt
    /// @param _maxSharesToSocialize maximum amount of shares to socialize
    function socializeBadDebt(
        address _badDebtVault,
        address _vaultAcceptor,
        uint256 _maxSharesToSocialize
    ) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        // reverts if vault is disconnected or a few other reasons from VaultHub logic
        try vaultHub.socializeBadDebt(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize) {
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

    /// @notice Function to force validator exits in VaultHub
    /// @param _vault Address of the vault to exit validators from
    /// @param _pubkeys Public keys of the validators to exit
    function forceValidatorExit(
        address _vault,
        bytes calldata _pubkeys
    ) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        uint256 fee = _getWithdrawalRequestFee();
        require(fee <= validatorExitFeeLimit, ERROR_VALIDATOR_EXIT_FEE_LIMIT_EXCEEDED);

        uint256 numKeys = _pubkeys.length / PUBLIC_KEY_LENGTH;
        uint256 value = fee * numKeys;
        require(value <= address(this).balance, ERROR_NOT_ENOUGH_ETH);

        // reverts if vault is disconnected or healthy
        try vaultHub.forceValidatorExit{value: value}(_vault, _pubkeys, address(this)) {
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

    /// @notice Function to set the validator exit fee limit
    /// @param _validatorExitFeeLimit new validator exit fee limit
    function setValidatorExitFeeLimit(uint256 _validatorExitFeeLimit) external onlyTrustedCaller(msg.sender) {
        require(_validatorExitFeeLimit > 0, ERROR_ZERO_VALIDATOR_EXIT_FEE_LIMIT);
        validatorExitFeeLimit = _validatorExitFeeLimit;

        emit WithdrawalRequestFeeUpdated(validatorExitFeeLimit, _validatorExitFeeLimit);
    }

    /// @notice Function to withdraw all ETH to TrustedCaller
    function withdrawETH(address _recipient) external onlyTrustedCaller(msg.sender) {
        uint256 balance = address(this).balance;
        require(balance > 0, ERROR_NO_ETH_TO_WITHDRAW);

        (bool success, ) = _recipient.call{value: balance}("");
        require(success, ERROR_ETH_TRANSFER_FAILED);
    }

    /// @dev Retrieves the current EIP-7002 withdrawal fee.
    /// @return The minimum fee required per withdrawal request.
    function _getWithdrawalRequestFee() internal view returns (uint256) {
        (bool success, bytes memory feeData) = WITHDRAWAL_REQUEST_PREDEPLOY_ADDRESS.staticcall("");

        require(success, ERROR_WITHDRAWAL_FEE_READ_FAILED);
        require(feeData.length == 32, ERROR_WITHDRAWAL_FEE_INVALID_DATA);

        return abi.decode(feeData, (uint256));
    }

    receive() external payable {}
}
