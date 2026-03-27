// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/ICSModule.sol";

/// @notice Minimal CSModule stub exposing mutable node operators count for testing
contract CSModuleNodeOperatorsStub is ICSModule {
    uint256 private _nodeOperatorsCount;
    address private _accounting;
    mapping(uint256 => bool) private _activeNodeOperators;

    function setNodeOperatorsCount(uint256 newCount) external {
        _nodeOperatorsCount = newCount;
    }

    function setNodeOperatorIsActive(uint256 nodeOperatorId, bool isActive) external {
        _activeNodeOperators[nodeOperatorId] = isActive;
    }

    function setAccounting(address accounting_) external {
        _accounting = accounting_;
    }

    function ACCOUNTING() external view override returns (address) {
        return _accounting;
    }

    function settleGeneralDelayedPenalty(uint256[] memory, uint256[] memory) external pure override {}

    function getNodeOperatorsCount() external view override returns (uint256) {
        return _nodeOperatorsCount;
    }

    function getNodeOperatorIsActive(uint256 nodeOperatorId) external view override returns (bool) {
        return _activeNodeOperators[nodeOperatorId];
    }

    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata) external pure override {}
}
