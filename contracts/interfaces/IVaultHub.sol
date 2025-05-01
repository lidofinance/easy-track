// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IVaultHub {
    struct VaultSocket {
        address vault;
        uint96 liabilityShares;
        uint96 shareLimit;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 treasuryFeeBP;
        bool pendingDisconnect;
        uint96 feeSharesCharged;
    }

    /// @notice Returns the role identifier for vault master
    /// @return The bytes32 role identifier for vault master
    function VAULT_MASTER_ROLE() external view returns (bytes32);

    /// @notice Returns the vault socket information for a given vault address
    /// @param _vault The address of the vault to query
    /// @return The VaultSocket struct containing vault configuration and state
    function vaultSocket(address _vault) external view returns (VaultSocket memory);

    /// @notice Updates the share limit for a specific vault
    /// @param _vault The address of the vault to update
    /// @param _shareLimit The new share limit value
    function updateShareLimit(address _vault, uint256 _shareLimit) external;

    /// @notice Updates the treasury fee basis points for a specific vault
    /// @param _vault The address of the vault to update
    /// @param _treasuryFeeBP The new treasury fee basis points value
    function updateTreasuryFeeBP(address _vault, uint256 _treasuryFeeBP) external;

    /// @notice connects a vault to the hub in permissionless way, get limits from the Operator Grid
    /// @param _vault vault address
    function connectVault(address _vault) external;
} 