// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @title Lido's accounting interface
interface IAccounting {
    struct BondLockData {
        uint128 amount;
        uint128 until;
    }

    /// @notice Get amount of the locked bond in ETH (stETH) by the given Node Operator
    /// @param nodeOperatorId ID of the Node Operator
    /// @return Amount of the actual locked bond
    function getLockedBond(uint256 nodeOperatorId) external view returns (uint256);

    /// @notice Get bond lock nonce for the given Node Operator
    /// @param nodeOperatorId ID of the Node Operator
    /// @return Bond lock nonce
    function getBondLockNonce(uint256 nodeOperatorId) external view returns (uint256);
}
