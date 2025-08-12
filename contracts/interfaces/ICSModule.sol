// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

 pragma solidity 0.8.6;

/// @title Lido's Community Staking Module interface
interface ICSModule {

    function ACCOUNTING() external view returns (address);

    /// @notice Settles blocked bond for the given Node Operators
    /// @dev Should be called by the Easy Track
    /// @param nodeOperatorIds IDs of the Node Operators
    /// @param maxAmounts Maximum amounts to settle for each Node Operator
    function settleELRewardsStealingPenalty(
        uint256[] memory nodeOperatorIds,
        uint256[] memory maxAmounts
    ) external;

    function getNodeOperatorsCount() external view returns (uint256);
}
