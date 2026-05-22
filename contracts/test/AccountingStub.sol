// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

/// @notice Test stub for CSAccounting (implements IAccounting methods).
contract AccountingStub {
    mapping(uint256 => uint256) internal _lockedBond;

    function getLockedBond(uint256 nodeOperatorId) external view returns (uint256) {
        return _lockedBond[nodeOperatorId];
    }

    function mock_setLockedBond(uint256 nodeOperatorId, uint256 amount) external {
        _lockedBond[nodeOperatorId] = amount;
    }

    function mock_clearLockedBond(uint256 nodeOperatorId) external {
        _lockedBond[nodeOperatorId] = 0;
    }
}
