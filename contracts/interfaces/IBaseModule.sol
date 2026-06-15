// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

struct WithdrawnValidatorInfo {
    uint256 nodeOperatorId;
    uint256 keyIndex;
    uint256 exitBalance;
    uint256 slashingPenalty;
    bool isSlashed;
}

/// @notice Minimal subset of CSM `IBaseModule` used by Easy Track factories.
interface IBaseModule {
    function ACCOUNTING() external view returns (address);

    function settleGeneralDelayedPenalty(
        uint256[] memory nodeOperatorIds,
        uint256[] memory maxAmounts
    ) external;

    function getNodeOperatorsCount() external view returns (uint256);

    function getNodeOperatorIsActive(uint256 nodeOperatorId) external view returns (bool);

    function isValidatorSlashed(uint256 nodeOperatorId, uint256 keyIndex) external view returns (bool);

    function reportValidatorSlashing(uint256 nodeOperatorId, uint256 keyIndex) external;

    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos) external;
}
