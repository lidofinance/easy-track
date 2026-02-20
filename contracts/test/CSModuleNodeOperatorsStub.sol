// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/ICSModule.sol";

/// @notice Minimal CSModule stub exposing mutable node operators count for testing
contract CSModuleNodeOperatorsStub is ICSModule {
    uint256 private _nodeOperatorsCount;

    function setNodeOperatorsCount(uint256 newCount) external {
        _nodeOperatorsCount = newCount;
    }

    function settleELRewardsStealingPenalty(uint256[] memory) external pure override {}

    function getNodeOperatorsCount() external view override returns (uint256) {
        return _nodeOperatorsCount;
    }
}
