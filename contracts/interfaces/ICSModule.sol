// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

struct WithdrawnValidatorInfo {
    uint256 nodeOperatorId;
    uint256 keyIndex;
    uint256 exitBalance;
    uint256 slashingPenalty;
    bool isSlashed;
}

/// @title Lido's Community Staking Module interface
interface ICSModule {

    function ACCOUNTING() external view returns (address);

    /// @notice Settles blocked bond for the given Node Operators
    /// @dev Should be called by the Easy Track
    /// @param nodeOperatorIds IDs of the Node Operators
    /// @param maxAmounts Maximum amounts to settle for each Node Operator
    function settleGeneralDelayedPenalty(
        uint256[] memory nodeOperatorIds,
        uint256[] memory maxAmounts
    ) external;

    function getNodeOperatorsCount() external view returns (uint256);

    function getNodeOperatorIsActive(uint256 nodeOperatorId) external view returns (bool);

    /// @notice Report withdrawn validators that have been slashed.
    /// @notice Called by the Easy Track EVM script executor via a motion started by the dedicated committee.
    /// @param validatorInfos An array WithdrawnValidatorInfo structs
    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos) external;
}
