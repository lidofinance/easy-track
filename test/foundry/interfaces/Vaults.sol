// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

// -----------------------------------------------------------------------------
// The Lido vaults contracts the operator grid and vault hub factories drive through
// `VaultsAdapter`, with the state-construction surface the scenarios need: creating vaults,
// reporting on them and minting against them. Names and struct layouts match
// contracts/interfaces/{IOperatorGrid,IVaultHub,IVaultFactory,ILazyOracle,IVaultsAdapter}.sol.
// -----------------------------------------------------------------------------

/// @notice A tier's parameters, the calldata entry of the tier factories.
struct TierParams {
    uint256 shareLimit;
    uint256 reserveRatioBP;
    uint256 forcedRebalanceThresholdBP;
    uint256 infraFeeBP;
    uint256 liquidityFeeBP;
    uint256 reservationFeeBP;
}

/// @notice The operator grid: groups of one node operator each, their tiers, and the jail.
interface IOperatorGrid {
    struct Group {
        address operator;
        uint96 shareLimit;
        uint96 liabilityShares;
        uint256[] tierIds;
    }

    struct Tier {
        address operator;
        uint96 shareLimit;
        uint96 liabilityShares;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 infraFeeBP;
        uint16 liquidityFeeBP;
        uint16 reservationFeeBP;
    }

    event VaultJailStatusUpdated(address indexed vault, bool isInJail);

    function REGISTRY_ROLE() external view returns (bytes32);

    function registerGroup(address _nodeOperator, uint256 _shareLimit) external;

    function updateGroupShareLimit(address _nodeOperator, uint256 _shareLimit) external;

    function registerTiers(address _nodeOperator, TierParams[] calldata _tiers) external;

    function alterTiers(uint256[] calldata _tierIds, TierParams[] calldata _tierParams) external;

    function group(address _nodeOperator) external view returns (Group memory);

    function tier(uint256 _tierId) external view returns (Tier memory);

    function tiersCount() external view returns (uint256);

    function isVaultInJail(address _vault) external view returns (bool);
}

/// @notice The vault hub: every connected vault's connection and record, reported on by the lazy
///         oracle and minted against by the vault's owner.
interface IVaultHub {
    struct VaultConnection {
        address owner;
        uint96 shareLimit;
        uint96 vaultIndex;
        uint48 disconnectInitiatedTs;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 infraFeeBP;
        uint16 liquidityFeeBP;
        uint16 reservationFeeBP;
        bool isBeaconDepositsManuallyPaused;
    }

    struct Report {
        uint104 totalValue;
        int104 inOutDelta;
        uint48 timestamp;
    }

    struct Int104WithCache {
        int104 value;
        int104 valueOnRefSlot;
        uint48 refSlot;
    }

    struct VaultRecord {
        Report report;
        uint96 maxLiabilityShares;
        uint96 liabilityShares;
        Int104WithCache[2] inOutDelta;
        uint128 minimalReserve;
        uint128 redemptionShares;
        uint128 cumulativeLidoFees;
        uint128 settledLidoFees;
    }

    event VaultFeesUpdated(
        address indexed vault,
        uint256 preInfraFeeBP,
        uint256 preLiquidityFeeBP,
        uint256 preReservationFeeBP,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    );

    event ForcedValidatorExitTriggered(
        address indexed vault, bytes pubkeys, address refundRecipient
    );

    event BadDebtSocialized(
        address indexed vaultDonor, address indexed vaultAcceptor, uint256 badDebtShares
    );

    event VaultRedemptionSharesUpdated(address indexed vault, uint256 redemptionShares);

    function BAD_DEBT_MASTER_ROLE() external view returns (bytes32);

    function VALIDATOR_EXIT_ROLE() external view returns (bytes32);

    function REDEMPTION_MASTER_ROLE() external view returns (bytes32);

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

    function mintShares(address _vault, address _recipient, uint256 _amountOfShares) external;

    function vaultsCount() external view returns (uint256);

    function vaultByIndex(uint256 _index) external view returns (address);

    function vaultConnection(address _vault) external view returns (VaultConnection memory);

    function vaultRecord(address _vault) external view returns (VaultRecord memory);
}

/// @notice The vault factory: a staking vault with its dashboard, connected to the hub.
interface IVaultFactory {
    struct RoleAssignment {
        address account;
        bytes32 role;
    }

    function createVaultWithDashboard(
        address _defaultAdmin,
        address _nodeOperator,
        address _nodeOperatorManager,
        uint256 _nodeOperatorFeeBP,
        uint256 _confirmExpiry,
        RoleAssignment[] calldata _roleAssignments
    ) external payable returns (address vault, address dashboard);
}

/// @notice The lazy oracle: the accounting oracle posts a report, then vault reports are applied
///         against it.
interface ILazyOracle {
    function updateReportData(
        uint256 _vaultsDataTimestamp,
        uint256 _vaultsDataRefSlot,
        bytes32 _vaultsDataTreeRoot,
        string calldata _vaultsDataReportCid
    ) external;
}

/// @notice `VaultsAdapter`, the executor's entry to the grid and the hub, deployed fresh by the
///         scenarios. The actions are what the factories' permissions name.
interface IVaultsAdapter {
    function trustedCaller() external view returns (address);

    function lidoLocator() external view returns (address);

    function evmScriptExecutor() external view returns (address);

    function validatorExitFeeLimit() external view returns (uint256);

    function updateVaultFees(
        address _vault,
        uint256 _infraFeeBP,
        uint256 _liquidityFeeBP,
        uint256 _reservationFeeBP
    ) external;

    function setVaultJailStatus(address _vault, bool _isInJail) external;

    function setLiabilitySharesTarget(address _vault, uint256 _liabilitySharesTarget) external;

    function socializeBadDebt(
        address _badDebtVault,
        address _vaultAcceptor,
        uint256 _maxSharesToSocialize
    ) external;

    function forceValidatorExit(address _vault, bytes calldata _pubkeys) external payable;
}
