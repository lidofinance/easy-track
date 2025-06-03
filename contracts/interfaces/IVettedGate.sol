// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

 pragma solidity 0.8.6;

/// @title Lido's Community Staking Module Vetted Gate interface
interface IVettedGate {
    /// @notice Set the root of the eligible members Merkle Tree
    /// @param _treeRoot New root of the Merkle Tree
    /// @param _treeCid New CID of the Merkle Tree
    function setTreeParams(
        bytes32 _treeRoot,
        string calldata _treeCid
    ) external;
}
