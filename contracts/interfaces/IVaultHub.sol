// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IVaultHub {
    struct VaultConnection {
        address owner;
        uint96 shareLimit;
        uint96 vaultIndex;
        bool pendingDisconnect;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 infraFeeBP;
        uint16 liquidityFeeBP;
        uint16 reservationFeeBP;
    }

    struct VaultRecord {
        uint128 totalValue;
        int128 inOutDelta;
        uint128 locked;
        uint96 liabilityShares;
        uint64 reportTimestamp;
        int128 reportInOutDelta;
        uint96 feeSharesCharged;
    }

    /// @notice Returns the role identifier for vault master
    /// @return The bytes32 role identifier for vault master
    function VAULT_MASTER_ROLE() external view returns (bytes32);

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
}
