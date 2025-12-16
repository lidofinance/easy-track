// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IVaultHub {
    struct VaultConnection {
        // ### 1st slot
        /// @notice address of the vault owner
        address owner;
        /// @notice maximum number of stETH shares that can be minted by vault owner
        uint96 shareLimit;
        // ### 2nd slot
        /// @notice index of the vault in the list of vaults. Indexes are not guaranteed to be stable.
        /// @dev vaultIndex is always greater than 0
        uint96 vaultIndex;
        /// @notice timestamp of the block when disconnection was initiated
        /// equal 0 if vault is disconnected and max(uint48) - for connected ,
        uint48 disconnectInitiatedTs;
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
        /// @notice if true, vault owner manually paused the beacon chain deposits
        bool isBeaconDepositsManuallyPaused;
        /// 24 bits gap
    }

    struct VaultRecord {
        // ### 1st slot
        /// @notice latest report for the vault
        Report report;
        // ### 2nd slot
        /// @notice max number of shares that was minted by the vault in current Oracle period
        /// (used to calculate the locked value on the vault)
        uint96 maxLiabilityShares;
        /// @notice liability shares of the vault
        uint96 liabilityShares;
        // ### 3rd and 4th slots
        /// @notice inOutDelta of the vault (all deposits - all withdrawals)
        Int104WithCache[2] inOutDelta;
        // ### 5th slot
        /// @notice the minimal value that the reserve part of the locked can be
        uint128 minimalReserve;
        /// @notice part of liability shares reserved to be burnt as Lido core redemptions
        uint128 redemptionShares;
        // ### 6th slot
        /// @notice cumulative value for Lido fees that accrued on the vault
        uint128 cumulativeLidoFees;
        /// @notice cumulative value for Lido fees that were settled on the vault
        uint128 settledLidoFees;
    }

    struct Int104WithCache {
        int104 value;
        int104 valueOnRefSlot;
        uint48 refSlot;
    }

    struct Report {
        /// @notice total value of the vault
        uint104 totalValue;
        /// @notice inOutDelta of the report
        int104 inOutDelta;
        /// @notice timestamp (in seconds)
        uint48 timestamp;
    }

    // -----------------------------
    //           FUNCTIONS
    // -----------------------------

    /// @notice connects a vault to the hub in permissionless way, get limits from the Operator Grid
    /// @param _vault vault address
    function connectVault(address _vault) external;

    /// @notice update of the vault data by the lazy oracle report
    /// @param _vault the address of the vault
    /// @param _reportTimestamp the timestamp of the report (last 32 bits of it)
    /// @param _reportTotalValue the total value of the vault
    /// @param _reportInOutDelta the inOutDelta of the vault
    /// @param _reportCumulativeLidoFees the cumulative Lido fees of the vault
    /// @param _reportLiabilityShares the liabilityShares of the vault on refSlot
    /// @param _reportMaxLiabilityShares the maxLiabilityShares of the vault on refSlot
    /// @param _reportSlashingReserve the slashingReserve of the vault
    function applyVaultReport(
        address _vault,
        uint256 _reportTimestamp,
        uint256 _reportTotalValue,
        int256 _reportInOutDelta,
        uint256 _reportCumulativeLidoFees,
        uint256 _reportLiabilityShares,
        uint256 _reportMaxLiabilityShares,
        uint256 _reportSlashingReserve
    ) external;

    /// @notice mint StETH shares backed by vault external balance to the receiver address
    /// @param _vault vault address
    /// @param _recipient address of the receiver
    /// @param _amountOfShares amount of stETH shares to mint
    /// @dev requires the fresh report
    function mintShares(address _vault, address _recipient, uint256 _amountOfShares) external;

    /// @notice Grants a role to an account
    /// @param role the role to grant
    /// @param account the account to grant the role to
    function grantRole(bytes32 role, address account) external;

    /// @notice updates a redemption shares on the vault
    /// @param _vault The address of the vault
    /// @param _liabilitySharesTarget maximum amount of liabilityShares that will be preserved, the rest will be
    ///         marked as redemptionShares. If value is greater than liabilityShares, redemptionShares are set to 0
    function setLiabilitySharesTarget(address _vault, uint256 _liabilitySharesTarget) external;

    /// @notice Transfer the bad debt from the donor vault to the acceptor vault
    /// @param _badDebtVault address of the vault that has the bad debt
    /// @param _vaultAcceptor address of the vault that will accept the bad debt
    /// @param _maxSharesToSocialize maximum amount of shares to socialize
    /// @return number of shares that was socialized
    function socializeBadDebt(
        address _badDebtVault,
        address _vaultAcceptor,
        uint256 _maxSharesToSocialize
    ) external returns (uint256);

    /// @notice Triggers validator full withdrawals for the vault using EIP-7002 if the vault has obligations shortfall
    /// @param _vault address of the vault to exit validators from
    /// @param _pubkeys array of public keys of the validators to exit
    /// @param _refundRecipient address that will receive the refund for transaction costs
    function forceValidatorExit(
        address _vault,
        bytes calldata _pubkeys,
        address _refundRecipient
    ) external payable;

    // -----------------------------
    //            VIEW FUNCTIONS
    // -----------------------------

    /// @notice returns the number of vaults connected to the hub
    /// @dev since index 0 is reserved for not connected vaults, it's always 1 less than the vaults array length
    function vaultsCount() external view returns (uint256);

    /// @notice returns the vault address by its index
    /// @param _index index of the vault in the 1-based list of vaults. possible range [1, vaultsCount()]
    /// @dev Indexes are guaranteed to be stable only in one transaction.
    function vaultByIndex(uint256 _index) external view returns (address);

    /// @notice Returns the vault connection information for a given vault address
    /// @param _vault The address of the vault to query
    /// @return The VaultConnection struct containing vault configuration
    function vaultConnection(address _vault) external view returns (VaultConnection memory);

    /// @notice Returns the vault record information for a given vault address
    /// @param _vault The address of the vault to query
    /// @return The VaultRecord struct containing vault state
    function vaultRecord(address _vault) external view returns (VaultRecord memory);

    /// @notice returns the vault's current obligations toward the protocol
    /// @param _vault vault address
    /// @return sharesToBurn amount of shares to burn / rebalance
    /// @return feesToSettle amount of Lido fees to settle
    function obligations(address _vault) external view returns (uint256 sharesToBurn, uint256 feesToSettle);

    /// @notice calculate ether amount required to cover obligations shortfall of the vault
    /// @param _vault vault address
    /// @return ether amount or UINT256_MAX if it's impossible to cover obligations shortfall
    /// @dev returns 0 if the vault is not connected
    function obligationsShortfallValue(address _vault) external view returns (uint256);

    /// @notice Returns true if vault is pending for disconnect, false if vault is connected or disconnected
    /// @param _vault vault address
    /// @return true if vault is pending for disconnect
    function isPendingDisconnect(address _vault) external view returns (bool);

    /// @return true if the vault is connected to the hub or pending to be disconnected
    function isVaultConnected(address _vault) external view returns (bool);

    /// @return true if the report for the vault is fresh, false otherwise
    /// @dev returns false if the vault is not connected
    function isReportFresh(address _vault) external view returns (bool);

    /// @notice Returns the bad debt master role
    /// @return bytes32 the bad debt master role
    function BAD_DEBT_MASTER_ROLE() external view returns (bytes32);

    /// @notice Returns the validator exit role
    /// @return bytes32 the validator exit role
    function VALIDATOR_EXIT_ROLE() external view returns (bytes32);

    /// @notice Returns the redemption master role
    /// @return bytes32 the redemption master role
    function REDEMPTION_MASTER_ROLE() external view returns (bytes32);

    // -----------------------------
    //            EVENTS
    // -----------------------------

    event VaultFeesUpdated(
        address indexed vault,
        uint256 preInfraFeeBP,
        uint256 preLiquidityFeeBP,
        uint256 preReservationFeeBP,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    );
    event ForcedValidatorExitTriggered(address indexed vault, bytes pubkeys, address refundRecipient);
    event BadDebtSocialized(address indexed vaultDonor, address indexed vaultAcceptor, uint256 badDebtShares);
    event VaultRedemptionSharesUpdated(address indexed vault, uint256 redemptionShares);
}
