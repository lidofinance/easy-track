// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/ILido.sol";

/// @notice Helper contract with a minimal Lido implementation for testing
contract LidoStub is ILido {
    uint256 private depositsReserveTarget;

    constructor(uint256 _depositsReserveTarget) {
        depositsReserveTarget = _depositsReserveTarget;
    }

    function setDepositsReserveTarget(uint256 _newDepositsReserveTarget) external override {
        depositsReserveTarget = _newDepositsReserveTarget;
    }

    function getDepositsReserveTarget() external view override returns (uint256) {
        return depositsReserveTarget;
    }
}
