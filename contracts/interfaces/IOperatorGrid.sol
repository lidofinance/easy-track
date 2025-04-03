// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

 pragma solidity 0.8.6;

/// @title Lido's Operator Grid interface
interface IOperatorGrid {
    // -----------------------------
    //            STRUCTS
    // -----------------------------
    struct Group {
        uint96 shareLimit;
        uint96 mintedShares;
        address operator;
        uint256[] tiersId;
        uint256[] vaultsIndex;
    }

    struct Tier {
        uint96 shareLimit;
        uint96 mintedShares;
        uint16 reserveRatioBP;
        uint16 rebalanceThresholdBP;
        uint16 treasuryFeeBP;
    }

    struct Vault {
        uint256 groupIndex;
        uint256 tierId;
    }

    struct TierParams {
        uint256 shareLimit;
        uint256 reserveRatioBP;
        uint256 rebalanceThresholdBP;
        uint256 treasuryFeeBP;
    }

    // -----------------------------
    //            FUNCTIONS
    // -----------------------------
    function registerGroup(address nodeOperator, uint256 shareLimit) external;
    function updateGroupShareLimit(address nodeOperator, uint256 newShareLimit) external;
    function registerTiers(
        address nodeOperator,
        TierParams[] calldata tiers
    ) external returns (uint256 tierId);

    // view functions
    function groupCount() external view returns (uint256);
    function groupByIndex(uint256 _index) external view returns (Group memory);
    function group(address _nodeOperator) external view returns (Group memory);
}
