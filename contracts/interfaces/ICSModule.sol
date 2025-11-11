// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

struct ValidatorWithdrawalInfo {
    uint256 nodeOperatorId;
    uint256 keyIndex;
    uint256 exitBalance;
    uint256 slashingPenalty;
}

/// @title Lido's Community Staking Module interface
interface ICSModule {
    /// @notice Settles blocked bond for the given Node Operators
    /// @dev Should be called by the Easy Track
    /// @param nodeOperatorIds IDs of the Node Operators
    function settleELRewardsStealingPenalty(uint256[] memory nodeOperatorIds) external;

    function getNodeOperatorsCount() external view returns (uint256);

    /// @notice Report Node Operator's keys as withdrawn and settle withdrawn amount
    /// @param withdrawalsInfo An array for the validator withdrawals info structs
    function submitWithdrawals(ValidatorWithdrawalInfo[] calldata withdrawalsInfo) external;
}
