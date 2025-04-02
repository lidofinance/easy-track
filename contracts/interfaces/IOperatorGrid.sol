// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

 pragma solidity 0.8.6;

/// @title Lido's Operator Grid interface
interface IOperatorGrid {
    // -----------------------------
    //            STRUCTS
    // -----------------------------
    struct Group {
        uint256 id;
        uint96 shareLimit;
        uint96 mintedShares;
        uint256[] tiers;
        uint256 tiersCount;
    }

    struct Tier {
        uint96 shareLimit;
        uint96 mintedShares;
        uint16 reserveRatioBP;
        uint16 rebalanceThresholdBP;
        uint16 treasuryFeeBP;
    }

    struct NodeOperator {
        uint256 groupId;
        uint256[] vaults;
        uint256 vaultsCount;
    }

    struct Vault {
        uint256 groupIndex;
        uint256 tierIndex;
        uint96 mintedShares;
    }

    // -----------------------------
    //            FUNCTIONS
    // -----------------------------
    function registerGroup(uint256 groupId, uint256 shareLimit) external;
    function updateGroupShareLimit(uint256 groupId, uint256 newShareLimit) external;
    function registerTier(
        uint256 groupId,
        uint256 tierId,
        uint256 shareLimit,
        uint256 reserveRatioBP,
        uint256 rebalanceThresholdBP,
        uint256 treasuryFeeBP
    ) external;
    function registerOperator(address _operator, uint256 _groupId) external;
    // view functions
    // TODO - remove redundant functions
    function groupCount() external view returns (uint256);
    function groupByIndex(uint256 _index) external view returns (Group memory);
    function group(uint256 _groupId) external view returns (Group memory);
    function nodeOperatorCount() external view returns (uint256);
    function nodeOperatorByIndex(uint256 _index) external view returns (NodeOperator memory);
    function nodeOperator(address _nodeOperator) external view returns (NodeOperator memory);
    function getVaultLimits(address vaultAddr) external view returns (
        uint256 shareLimit,
        uint256 reserveRatioBP,
        uint256 rebalanceThresholdBP,
        uint256 treasuryFeeBP
    );
}
