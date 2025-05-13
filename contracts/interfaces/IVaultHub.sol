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
        uint16 infraFeeBP;
        uint16 liquidityFeeBP;
        uint16 reservationFeeBP;
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

    /// @notice updates share limits for multiple vaults at once
    /// @param _vaults array of vault addresses
    /// @param _shareLimits array of new share limits
    function updateShareLimits(address[] calldata _vaults, uint256[] calldata _shareLimits) external;

    /// @notice updates fees for multiple vaults at once
    /// @param _vaults array of vault addresses
    /// @param _infraFeesBP array of new infra fees
    /// @param _liquidityFeesBP array of new liquidity fees
    /// @param _reservationFeesBP array of new reservation fees
    function updateVaultsFees(
        address[] calldata _vaults,
        uint256[] calldata _infraFeesBP,
        uint256[] calldata _liquidityFeesBP,
        uint256[] calldata _reservationFeesBP
    ) external;

    /// @notice connects a vault to the hub in permissionless way, get limits from the Operator Grid
    /// @param _vault vault address
    function connectVault(address _vault) external;
} 