// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Minimal subset of `ILido` used by Easy Track factories.
interface ILido {
    function setDepositsReserveTarget(uint256 _newDepositsReserveTarget) external;

    function getDepositsReserveTarget() external view returns (uint256);
}
