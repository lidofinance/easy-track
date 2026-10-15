// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @title Merkle Gate Interface
/// @notice Common surface for gates that guard node operator creation via Merkle proofs.
interface IMerkleGate {
    /// @return treeRoot Current Merkle tree root
    function treeRoot() external view returns (bytes32);

    /// @return treeCid Current Merkle tree CID
    function treeCid() external view returns (string memory);

    /// @notice Update Merkle tree params
    /// @param _treeRoot New root
    /// @param _treeCid New CID
    function setTreeParams(
        bytes32 _treeRoot,
        string calldata _treeCid
    ) external;
}