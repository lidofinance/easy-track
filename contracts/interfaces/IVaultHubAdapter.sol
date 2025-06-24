// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @title Interface for VaultHubAdapter
/// @notice Adapter for VaultHub to be used in EVMScriptFactories
interface IVaultHubAdapter {
    // -------------
    // VIEW FUNCTIONS
    // -------------

    /// @notice Fee limit for validator exits
    function validatorExitFeeLimit() external view returns (uint256);

    // -------------
    // EXTERNAL FUNCTIONS
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
    ) external;

    /// @notice Updates share limit for a vault
    /// @param _vault address of the vault to update
    /// @param _shareLimit new share limit value
    function updateShareLimit(address _vault, uint256 _shareLimit) external;

    /// @notice Socializes bad debt for a vault
    /// @param _badDebtVault address of the vault that has the bad debt
    /// @param _vaultAcceptor address of the vault that will accept the bad debt or 0 if the bad debt is internalized to the protocol
    /// @param _maxSharesToSocialize maximum amount of shares to socialize
    function socializeBadDebt(
        address _badDebtVault,
        address _vaultAcceptor,
        uint256 _maxSharesToSocialize
    ) external;

    /// @notice Function to force validator exits in VaultHub
    /// @param _vault Address of the vault to exit validators from
    /// @param _pubkeys Public keys of the validators to exit
    function forceValidatorExit(
        address _vault,
        bytes calldata _pubkeys
    ) external payable;

    /// @notice Function to set the validator exit fee limit
    /// @param _validatorExitFeeLimit new validator exit fee limit
    function setValidatorExitFeeLimit(uint256 _validatorExitFeeLimit) external;

    /// @notice Function to withdraw all ETH to TrustedCaller
    function withdrawETH() external;
} 
