// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

 pragma solidity 0.8.6;

/// @title Lido's Community Staking Module interface
interface ICSModule {
    /// @notice Settles blocked bond for the given Node Operators
    /// @dev Should be called by the Easy Track
    /// @param nodeOperatorIds IDs of the Node Operators
    function settleELRewardsStealingPenalty(
        uint256[] memory nodeOperatorIds
    ) external;

    function getNodeOperatorsCount() external view returns (uint256);
}
