// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @title Lido's accounting interface
interface IAccounting {
    struct BondLockData {
        uint128 amount;
        uint128 until;
    }

    /// @notice Get information about the locked bond for the given Node Operator
    /// @param nodeOperatorId ID of the Node Operator
    /// @return Locked bond info
    function getLockedBondInfo(uint256 nodeOperatorId) external view returns (BondLockData memory);

}
