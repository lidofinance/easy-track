// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {IAccounting} from "contracts/interfaces/IAccounting.sol";

/// @notice Test stub for Accounting.
contract AccountingStub is IAccounting {
    mapping(uint256 => uint256) internal _lockAmount;
    mapping(uint256 => uint256) internal _lockNonce;

    function getBondLockNonce(uint256 nodeOperatorId) external view override returns (uint256) {
        return _lockNonce[nodeOperatorId];
    }

    function getLockedBond(uint256 nodeOperatorId) external view override returns (uint256) {
        return _lockAmount[nodeOperatorId];
    }

    function mock_setLock(uint256 nodeOperatorId, uint256 amount, uint256 nonce) external {
        _lockAmount[nodeOperatorId] = amount;
        _lockNonce[nodeOperatorId] = nonce;
    }

    function mock_clearLock(uint256 nodeOperatorId) external {
        delete _lockAmount[nodeOperatorId];
        delete _lockNonce[nodeOperatorId];
    }
}
