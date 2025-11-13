// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMerkleGate.sol";
import "../interfaces/IAllowedMerkleGatesRegistry.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to set tree for Module's Gate that implements IMerkleGate
contract SetMerkleGateTree is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_GATE_NOT_ALLOWED =
        "GATE_NOT_ALLOWED";
    string private constant ERROR_EMPTY_TREE_ROOT =
        "EMPTY_TREE_ROOT";
    string private constant ERROR_EMPTY_TREE_CID =
        "EMPTY_TREE_CID";
    string private constant ERROR_SAME_TREE_CID =
        "SAME_TREE_CID";
    string private constant ERROR_SAME_TREE_ROOT =
        "SAME_TREE_ROOT";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of AllowedMerkleGatesRegistry contract
    IAllowedMerkleGatesRegistry public immutable allowedMerkleGatesRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _allowedMerkleGatesRegistry)
        TrustedCaller(_trustedCaller)
    {
        allowedMerkleGatesRegistry = IAllowedMerkleGatesRegistry(_allowedMerkleGatesRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set treeRoot and treeCid for Module's Gate
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address gate, bytes32 treeRoot, string treeCid) where
    /// gate - address of gate implementing IMerkleGate
    /// treeRoot - root of the Merkle tree
    /// treeCid - CID of the Merkle tree
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address gate, bytes32 treeRoot, string memory treeCid) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(gate, treeRoot, treeCid);

        return EVMScriptCreator.createEVMScript(
            gate,
            IMerkleGate.setTreeParams.selector,
            abi.encode(treeRoot, treeCid)
        );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: bytes32 treeRoot and string treeCid
    /// @return gate The address of the gate
    /// @return treeRoot The root of the tree
    /// @return treeCid The CID of the tree
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address, bytes32, string memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        private
        pure
        returns (address, bytes32, string memory)
    {
        return abi.decode(_evmScriptCallData, (address, bytes32, string));
    }

    function _validateInputData(
        address gate,
        bytes32 treeRoot,
        string memory treeCid
    ) private view {
        require(allowedMerkleGatesRegistry.isGateAllowed(gate), ERROR_GATE_NOT_ALLOWED);
        require(treeRoot != bytes32(0), ERROR_EMPTY_TREE_ROOT);
        require(bytes(treeCid).length > 0, ERROR_EMPTY_TREE_CID);
        require(treeRoot != IMerkleGate(gate).treeRoot(), ERROR_SAME_TREE_ROOT);
        require(keccak256(bytes(treeCid)) != keccak256(bytes(IMerkleGate(gate).treeCid())), ERROR_SAME_TREE_CID);
    }
}
