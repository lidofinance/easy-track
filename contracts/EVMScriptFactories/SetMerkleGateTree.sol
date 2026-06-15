// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMerkleGate.sol";

interface ISetMerkleGateTree is IEVMScriptFactory {
    function validateInputData(
        address gate,
        bytes32 currentTreeRoot,
        string memory currentTreeCid,
        bytes32 newTreeRoot,
        string memory newTreeCid
    ) external view;
}

/// @author vgorkavenko
/// @notice Creates EVMScript to set tree for Module's Gate that implements IMerkleGate
contract SetMerkleGateTree is TrustedCaller, ISetMerkleGateTree {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_EMPTY_TREE_ROOT = "EMPTY_TREE_ROOT";
    string private constant ERROR_EMPTY_TREE_CID = "EMPTY_TREE_CID";
    string private constant ERROR_SAME_TREE_CID = "SAME_TREE_CID";
    string private constant ERROR_SAME_TREE_ROOT = "SAME_TREE_ROOT";
    string private constant ERROR_CURRENT_VALUES_MISMATCH = "CURRENT_VALUES_MISMATCH";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Alias for factory (e.g. "CSMv3")
    string public name;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, string memory _name) TrustedCaller(_trustedCaller) {
        name = _name;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set treeRoot and treeCid for Module's Gate
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple:
    ///   (address gate, bytes32 currentTreeRoot, string currentTreeCid, bytes32 newTreeRoot, string newTreeCid)
    /// where
    ///   gate - address of gate implementing IMerkleGate
    ///   currentTreeRoot - expected current root of the Merkle tree
    ///   currentTreeCid - expected current CID of the Merkle tree
    ///   newTreeRoot - new root of the Merkle tree
    ///   newTreeCid - new CID of the Merkle tree
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address gate,
            bytes32 currentTreeRoot,
            string memory currentTreeCid,
            bytes32 newTreeRoot,
            string memory newTreeCid
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        validateInputData(gate, currentTreeRoot, currentTreeCid, newTreeRoot, newTreeCid);

        address[] memory toAddresses = new address[](2);
        bytes4[] memory methodIds = new bytes4[](2);
        bytes[] memory data = new bytes[](2);

        toAddresses[0] = address(this);
        methodIds[0] = ISetMerkleGateTree.validateInputData.selector;
        data[0] = abi.encode(gate, currentTreeRoot, currentTreeCid, newTreeRoot, newTreeCid);

        toAddresses[1] = gate;
        methodIds[1] = IMerkleGate.setTreeParams.selector;
        data[1] = abi.encode(newTreeRoot, newTreeCid);

        return EVMScriptCreator.createEVMScript(toAddresses, methodIds, data);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple:
    ///   (address gate, bytes32 currentTreeRoot, string currentTreeCid, bytes32 newTreeRoot, string newTreeCid)
    /// @return gate The address of the gate
    /// @return currentTreeRoot The expected current root of the tree
    /// @return currentTreeCid The expected current CID of the tree
    /// @return newTreeRoot The new root of the tree
    /// @return newTreeCid The new CID of the tree
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (
            address,
            bytes32,
            string memory,
            bytes32,
            string memory
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function validateInputData(
        address gate,
        bytes32 currentTreeRoot,
        string memory currentTreeCid,
        bytes32 newTreeRoot,
        string memory newTreeCid
    ) public view override {
        _validateInputData(gate, currentTreeRoot, currentTreeCid, newTreeRoot, newTreeCid);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        private
        pure
        returns (
            address,
            bytes32,
            string memory,
            bytes32,
            string memory
        )
    {
        return abi.decode(_evmScriptCallData, (address, bytes32, string, bytes32, string));
    }

    function _validateInputData(
        address gate,
        bytes32 currentTreeRoot,
        string memory currentTreeCid,
        bytes32 newTreeRoot,
        string memory newTreeCid
    ) private view {
        IMerkleGate merkleGate = IMerkleGate(gate);
        bytes32 onChainTreeRoot = merkleGate.treeRoot();
        bytes32 onChainTreeCidHash = keccak256(bytes(merkleGate.treeCid()));

        require(currentTreeRoot == onChainTreeRoot, ERROR_CURRENT_VALUES_MISMATCH);
        require(
            keccak256(bytes(currentTreeCid)) == onChainTreeCidHash,
            ERROR_CURRENT_VALUES_MISMATCH
        );
        require(newTreeRoot != bytes32(0), ERROR_EMPTY_TREE_ROOT);
        require(bytes(newTreeCid).length > 0, ERROR_EMPTY_TREE_CID);
        require(newTreeRoot != onChainTreeRoot, ERROR_SAME_TREE_ROOT);
        require(keccak256(bytes(newTreeCid)) != onChainTreeCidHash, ERROR_SAME_TREE_CID);
    }
}
