// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

 pragma solidity 0.8.6;

/// @title Lido's CSM accounting interface
interface ICSAccounting {
    /// @notice Get amount of the locked bond in ETH (stETH) by the given Node Operator
    /// @param nodeOperatorId ID of the Node Operator
    /// @return Amount of the actual locked bond
    function getActualLockedBond(
        uint256 nodeOperatorId
    ) external view returns (uint256);
}
