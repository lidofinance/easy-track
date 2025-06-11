// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @title Lido's OperatorGrid interface
interface IOperatorGrid {
    // -----------------------------
    //            STRUCTS
    // -----------------------------
    struct Group {
        address operator;
        uint96 shareLimit;
        uint96 liabilityShares;
        uint64[] tierIds;
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

    struct TierParams {
        uint256 shareLimit;
        uint256 reserveRatioBP;
        uint256 forcedRebalanceThresholdBP;
        uint256 infraFeeBP;
        uint256 liquidityFeeBP;
        uint256 reservationFeeBP;
    }

    // -----------------------------
    //            FUNCTIONS
    // -----------------------------
    
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
}
