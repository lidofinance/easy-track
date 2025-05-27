// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IVaultHub {
    struct VaultConnection {
        /// @notice address of the vault owner
        address owner;
        /// @notice maximum number of stETH shares that can be minted by vault owner
        uint96 shareLimit;
        /// @notice index of the vault in the list of vaults. Indexes is guaranteed to be stable only if there was no deletions.
        /// @dev vaultIndex is always greater than 0
        uint96 vaultIndex;
        /// @notice if true, vault is disconnected and fee is not accrued
        bool pendingDisconnect;
        /// @notice share of ether that is locked on the vault as an additional reserve
        /// e.g RR=30% means that for 1stETH minted 1/(1-0.3)=1.428571428571428571 ETH is locked on the vault
        uint16 reserveRatioBP;
        /// @notice if vault's reserve decreases to this threshold, it should be force rebalanced
        uint16 forcedRebalanceThresholdBP;
        /// @notice infra fee in basis points
        uint16 infraFeeBP;
        /// @notice liquidity fee in basis points
        uint16 liquidityFeeBP;
        /// @notice reservation fee in basis points
        uint16 reservationFeeBP;
    }

    struct VaultRecord {
        /// @notice latest report for the vault
        Report report;
        /// @notice amount of ether that is locked from withdrawal on the vault
        uint128 locked;
        /// @notice liability shares of the vault
        uint96 liabilityShares;
        /// @notice timestamp of the latest report
        uint64 reportTimestamp;
        /// @notice current inOutDelta of the vault (all deposits - all withdrawals)
        int128 inOutDelta;
    }

    struct Report {
        /// @notice total value of the vault
        uint128 totalValue;
        /// @notice inOutDelta of the report
        int128 inOutDelta;
    }

    /// @notice Returns the role identifier for vault master
    /// @return The bytes32 role identifier for vault master
    function VAULT_MASTER_ROLE() external view returns (bytes32);

    /// @notice Returns the role identifier for withdrawal executor
    /// @return The bytes32 role identifier for withdrawal executor
    function WITHDRAWAL_EXECUTOR_ROLE() external view returns (bytes32);

    /// @notice Returns the vault connection information for a given vault address
    /// @param _vault The address of the vault to query
    /// @return The VaultConnection struct containing vault configuration
    function vaultConnection(address _vault) external view returns (VaultConnection memory);

    /// @notice Returns the vault record information for a given vault address
    /// @param _vault The address of the vault to query
    /// @return The VaultRecord struct containing vault state
    function vaultRecord(address _vault) external view returns (VaultRecord memory);

    /// @notice updates share limit for the vault
    /// @param _vault vault address
    /// @param _shareLimit new share limit
    function updateShareLimit(address _vault, uint256 _shareLimit) external;

    /// @notice updates fees for the vault
    /// @param _vault vault address
    /// @param _infraFeeBP new infra fee in basis points
    /// @param _liquidityFeeBP new liquidity fee in basis points
    /// @param _reservationFeeBP new reservation fee in basis points
    function updateVaultFees(
        address _vault,
        uint256 _infraFeeBP,
        uint256 _liquidityFeeBP,
        uint256 _reservationFeeBP
    ) external;

    /// @notice connects a vault to the hub in permissionless way, get limits from the Operator Grid
    /// @param _vault vault address
    function connectVault(address _vault) external;

    /// @notice Triggers validator full withdrawals for the vault using EIP-7002 permissionlessly if the vault is unhealthy
    /// @param _vault address of the vault to exit validators from
    /// @param _pubkeys public keys of the validators to exit
    /// @param _refundRecipient address that will receive the refund for transaction costs
    /// @dev    When the vault becomes unhealthy, withdrawal committee can force its validators to exit the beacon chain
    ///         This returns the vault's deposited ETH back to vault's balance and allows to rebalance the vault
    function forceValidatorExits(
        address _vault,
        bytes calldata _pubkeys,
        address _refundRecipient
    ) external payable;
}
