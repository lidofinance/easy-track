// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Test stub for CSAccounting (implements IAccounting methods).
contract AccountingStub {
    struct BondLockData {
        uint128 amount;
        uint128 until;
    }

    mapping(uint256 => BondLockData) internal _lockedBondInfo;

    function getLockedBondInfo(uint256 nodeOperatorId) external view returns (BondLockData memory) {
        return _lockedBondInfo[nodeOperatorId];
    }

    function mock_setLockedBondInfo(uint256 nodeOperatorId, uint128 amount, uint128 until) external {
        _lockedBondInfo[nodeOperatorId] = BondLockData(amount, until);
    }

    function mock_clearLockedBond(uint256 nodeOperatorId) external {
        delete _lockedBondInfo[nodeOperatorId];
    }
}
