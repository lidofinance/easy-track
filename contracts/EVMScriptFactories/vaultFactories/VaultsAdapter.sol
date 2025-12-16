// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../interfaces/IVaultHub.sol";
import "../../interfaces/IOperatorGrid.sol";
import "../../interfaces/ILidoLocator.sol";

/// @author dry914
/// @notice Adapter for VaultHub and OperatorGrid to be used in EVMScriptFactories
contract VaultsAdapter is TrustedCaller {
    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ONLY_EVM_SCRIPT_EXECUTOR = "ONLY_EVM_SCRIPT_EXECUTOR";
    string private constant ERROR_OUT_OF_GAS = "OUT_OF_GAS";
    string private constant ERROR_NOT_ENOUGH_ETH = "NOT_ENOUGH_ETH";
    string private constant ERROR_NO_ETH_TO_WITHDRAW = "NO_ETH_TO_WITHDRAW";
    string private constant ERROR_ETH_TRANSFER_FAILED = "ETH_TRANSFER_FAILED";
    string private constant ERROR_ZERO_LIDO_LOCATOR = "ZERO_LIDO_LOCATOR";
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

    /// @notice Address of Lido Locator
    ILidoLocator public immutable lidoLocator;

    /// @notice Address of the EVMScriptExecutor
    address public immutable evmScriptExecutor;

    /// @notice Fee limit for validator exits
    uint256 public validatorExitFeeLimit;

    // -------------
    // EVENTS
    // -------------

    event VaultJailStatusUpdateFailed(address indexed vault, bool isInJail);
    event VaultFeesUpdateFailed(address indexed vault, uint256 infraFeeBP, uint256 liquidityFeeBP, uint256 reservationFeeBP);
    event LiabilitySharesTargetUpdateFailed(address indexed vault, uint256 liabilitySharesTarget);
    event BadDebtSocializationFailed(address indexed badDebtVault, address indexed vaultAcceptor, uint256 maxSharesToSocialize);
    event ForceValidatorExitFailed(address indexed vault, bytes pubkeys);
    event ValidatorExitFeeLimitUpdated(uint256 oldFee, uint256 newFee);

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLocator, address _evmScriptExecutor, uint256 _validatorExitFeeLimit)
        TrustedCaller(_trustedCaller)
    {
        require(_lidoLocator != address(0), ERROR_ZERO_LIDO_LOCATOR);
        require(_evmScriptExecutor != address(0), ERROR_ZERO_EVM_SCRIPT_EXECUTOR);
        require(_validatorExitFeeLimit > 0, ERROR_ZERO_VALIDATOR_EXIT_FEE_LIMIT);

        lidoLocator = ILidoLocator(_lidoLocator);
        evmScriptExecutor = _evmScriptExecutor;
        validatorExitFeeLimit = _validatorExitFeeLimit;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Function to update vault fees in OperatorGrid
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

        IVaultHub vaultHub = IVaultHub(lidoLocator.vaultHub());
        if (!vaultHub.isVaultConnected(_vault) || // vault is not connected to hub
            vaultHub.isPendingDisconnect(_vault)) { // vault is disconnecting
            emit VaultFeesUpdateFailed(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
            return;
        }

        IOperatorGrid operatorGrid = IOperatorGrid(lidoLocator.operatorGrid());
        operatorGrid.updateVaultFees(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
    }

    /// @notice Sets jail status for a vault in OperatorGrid
    /// @param _vault address of the vault to update
    /// @param _isInJail jail status to set
    function setVaultJailStatus(address _vault, bool _isInJail) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        IOperatorGrid operatorGrid = IOperatorGrid(lidoLocator.operatorGrid());
        if (operatorGrid.isVaultInJail(_vault) == _isInJail) { // status is already the same
            emit VaultJailStatusUpdateFailed(_vault, _isInJail);
            return;
        }

        operatorGrid.setVaultJailStatus(_vault, _isInJail);
    }

    /// @notice Sets liability shares target for a vault
    /// @param _vault address of the vault to update
    /// @param _liabilitySharesTarget new liability shares target value
    function setLiabilitySharesTarget(address _vault, uint256 _liabilitySharesTarget) external {
        require(msg.sender == evmScriptExecutor, ERROR_ONLY_EVM_SCRIPT_EXECUTOR);

        IVaultHub vaultHub = IVaultHub(lidoLocator.vaultHub());
        if (!vaultHub.isVaultConnected(_vault) || // vault is not connected to hub
            vaultHub.isPendingDisconnect(_vault)) { // vault is disconnecting
            emit LiabilitySharesTargetUpdateFailed(_vault, _liabilitySharesTarget);
            return;
        }

        vaultHub.setLiabilitySharesTarget(_vault, _liabilitySharesTarget);
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

        IVaultHub vaultHub = IVaultHub(lidoLocator.vaultHub());
        if (!vaultHub.isVaultConnected(_badDebtVault) || // vault is not connected to hub
            !vaultHub.isVaultConnected(_vaultAcceptor) || // vault is not connected to hub
            vaultHub.isPendingDisconnect(_badDebtVault) || // vault is disconnecting
            vaultHub.isPendingDisconnect(_vaultAcceptor)) { // vault is disconnecting
            emit BadDebtSocializationFailed(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize);
            return;
        }

        vaultHub.socializeBadDebt(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize);
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

        IVaultHub vaultHub = IVaultHub(lidoLocator.vaultHub());
        if (!vaultHub.isVaultConnected(_vault) || // vault is not connected to hub
            vaultHub.isPendingDisconnect(_vault) || // vault is disconnecting
            vaultHub.obligationsShortfallValue(_vault) == 0) { // vault has no obligations shortfall
            emit ForceValidatorExitFailed(_vault, _pubkeys);
            return;
        }

        vaultHub.forceValidatorExit{value: value}(_vault, _pubkeys, address(this));
    }

    /// @notice Function to set the validator exit fee limit
    /// @param _validatorExitFeeLimit new validator exit fee limit
    function setValidatorExitFeeLimit(uint256 _validatorExitFeeLimit) external onlyTrustedCaller(msg.sender) {
        require(_validatorExitFeeLimit > 0, ERROR_ZERO_VALIDATOR_EXIT_FEE_LIMIT);

        uint256 oldFee = validatorExitFeeLimit;
        validatorExitFeeLimit = _validatorExitFeeLimit;

        emit ValidatorExitFeeLimitUpdated(oldFee, _validatorExitFeeLimit);
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
