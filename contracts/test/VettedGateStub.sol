// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

/// @author vgorkavenko  
/// @notice Helper contract with stub implementation of VettedGate for testing
contract VettedGateStub is AccessControl {
    bytes32 public constant SET_TREE_ROLE = keccak256("SET_TREE_ROLE");
    
    bytes32 public treeRoot;
    string public treeCid;
    
    event TreeParamsSet(bytes32 indexed treeRoot, string treeCid);

    constructor() {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(SET_TREE_ROLE, msg.sender);
    }

    /// @notice Set the root of the eligible members Merkle Tree
    /// @param _treeRoot New root of the Merkle Tree
    /// @param _treeCid New CID of the Merkle Tree
    function setTreeParams(
        bytes32 _treeRoot,
        string calldata _treeCid
    ) external onlyRole(SET_TREE_ROLE) {
        treeRoot = _treeRoot;
        treeCid = _treeCid;
        
        emit TreeParamsSet(_treeRoot, _treeCid);
    }
}
