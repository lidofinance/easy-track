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
    /// @notice Settles blocked bond for the given Node Operators
    /// @dev Should be called by the Easy Track
    /// @param nodeOperatorIds IDs of the Node Operators
    function settleELRewardsStealingPenalty(uint256[] memory nodeOperatorIds) external;

    function getNodeOperatorsCount() external view returns (uint256);

    /// @notice Report Node Operator's keys as withdrawn and charge penalties associated with exit if any.
    ///         A validator is considered withdrawn in the following cases:
    ///         - if it's an exit of a non-slashed validator, when a withdrawal of the validator is included in a beacon
    ///           block;
    ///         - if it's an exit of a slashed validator, when the committee reports such a validator as withdrawn; note
    ///           that it can happen earlier than the actual withdrawal is included on the beacon chain if the committee
    ///           decides it can account for all penalties in advance;
    ///         - if it's a consolidated validator, when the corresponding pending consolidation is processed and the
    ///           balance of the validator has been moved to another validator.
    /// @notice Called by `CSVerifier` contract.
    /// @param validatorInfos An array WithdrawnValidatorInfo structs
    function reportWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos) external;
}
