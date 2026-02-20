// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IAllowedMerkleGatesRegistry {
    function name() external view returns (string memory);

    function isGateAllowed(address _gate) external view returns (bool);
}
