// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

struct TierParams {
    uint256 shareLimit;
    uint256 reserveRatioBP;
    uint256 forcedRebalanceThresholdBP;
    uint256 infraFeeBP;
    uint256 liquidityFeeBP;
    uint256 reservationFeeBP;
}

/// @title Lido's OperatorGrid interface
interface IOperatorGrid {
    // -----------------------------
    //            STRUCTS
    // -----------------------------
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

    // -----------------------------
    //            FUNCTIONS
    // -----------------------------

    /// @notice Grants a role to an account
    /// @param role the role to grant
    /// @param account the account to grant the role to
    function grantRole(bytes32 role, address account) external;

    /// @notice Registers a new group
    /// @param _nodeOperator address of the node operator
    /// @param _shareLimit Maximum share limit for the group
    function registerGroup(address _nodeOperator, uint256 _shareLimit) external;

    /// @notice Updates the share limit of a group
    /// @param _nodeOperator address of the node operator
    /// @param _shareLimit New share limit value
    function updateGroupShareLimit(address _nodeOperator, uint256 _shareLimit) external;

    /// @notice Registers a new tier
    /// @param _nodeOperator address of the node operator
    /// @param _tiers array of tiers to register
    function registerTiers(
        address _nodeOperator,
        TierParams[] calldata _tiers
    ) external;

    /// @notice Alters multiple tiers
    /// @param _tierIds array of tier ids to alter
    /// @param _tierParams array of new tier params
    function alterTiers(uint256[] calldata _tierIds, TierParams[] calldata _tierParams) external;

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

    /// @notice Updates if the vault is in jail
    /// @param _vault vault address
    /// @param _isInJail true if the vault is in jail, false otherwise
    function setVaultJailStatus(address _vault, bool _isInJail) external;

    // -----------------------------
    //            VIEW FUNCTIONS
    // -----------------------------

    /// @notice Returns a group by node operator address
    /// @param _nodeOperator address of the node operator
    /// @return Group
    function group(address _nodeOperator) external view returns (Group memory);

    /// @notice Returns a tier by ID
    /// @param _tierId id of the tier
    /// @return Tier
    function tier(uint256 _tierId) external view returns (Tier memory);

    /// @notice Returns the number of tiers
    /// @return Number of tiers
    function tiersCount() external view returns (uint256);

    /// @notice Returns true if the vault is in jail
    /// @param _vault address of the vault
    /// @return true if the vault is in jail
    function isVaultInJail(address _vault) external view returns (bool);

    /// @notice Returns the registry role
    /// @return bytes32 the registry role
    function REGISTRY_ROLE() external view returns (bytes32);

    /// @notice Get vault tier limits
    /// @param _vault address of the vault
    /// @return nodeOperator node operator of the vault
    /// @return tierId tier id of the vault
    /// @return shareLimit share limit of the vault
    /// @return reserveRatioBP reserve ratio of the vault
    /// @return forcedRebalanceThresholdBP forced rebalance threshold of the vault
    /// @return infraFeeBP infra fee of the vault
    /// @return liquidityFeeBP liquidity fee of the vault
    /// @return reservationFeeBP reservation fee of the vault
    function vaultTierInfo(address _vault)
        external
        view
        returns (
            address nodeOperator,
            uint256 tierId,
            uint256 shareLimit,
            uint256 reserveRatioBP,
            uint256 forcedRebalanceThresholdBP,
            uint256 infraFeeBP,
            uint256 liquidityFeeBP,
            uint256 reservationFeeBP
        );

    // -----------------------------
    //            EVENTS
    // -----------------------------
    event GroupAdded(address indexed nodeOperator, uint256 shareLimit);
    event GroupShareLimitUpdated(address indexed nodeOperator, uint256 shareLimit);
    event TierAdded(
        address indexed nodeOperator,
        uint256 indexed tierId,
        uint256 shareLimit,
        uint256 reserveRatioBP,
        uint256 forcedRebalanceThresholdBP,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    );
    event TierChanged(address indexed vault, uint256 indexed tierId, uint256 shareLimit);
    event TierUpdated(
      uint256 indexed tierId,
      uint256 shareLimit,
      uint256 reserveRatioBP,
      uint256 forcedRebalanceThresholdBP,
      uint256 infraFeeBP,
      uint256 liquidityFeeBP,
      uint256 reservationFeeBP
    );
    event VaultJailStatusUpdated(address indexed vault, bool isInJail);
}
