// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMerkleGate.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to set tree for Module's Gate that implements IMerkleGate
contract SetMerkleGateTree is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

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

    /// @notice Alias for factory (e.g. "IdentifiedCommunityStakerSetTreeParams")
    string public name;

    /// @notice Address of Module's Gate that implements IMerkleGate
    IMerkleGate public immutable merkleGate;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, string memory _name, address _merkleGate)
        TrustedCaller(_trustedCaller)
    {
        name = _name;
        merkleGate = IMerkleGate(_merkleGate);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set treeRoot and treeCid for Module's Gate
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: bytes32 treeRoot and string treeCid
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 treeRoot, string memory treeCid) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(treeRoot, treeCid);

        return
            EVMScriptCreator.createEVMScript(
                address(merkleGate),
                IMerkleGate.setTreeParams.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: bytes32 treeRoot and string treeCid
    /// @return treeRoot The root of the tree
    /// @return treeCid The CID of the tree
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (bytes32, string memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        private
        pure
        returns (bytes32, string memory)
    {
        return abi.decode(_evmScriptCallData, (bytes32, string));
    }

    function _validateInputData(
        bytes32 treeRoot,
        string memory treeCid
    ) private view {
        require(treeRoot != bytes32(0), ERROR_EMPTY_TREE_ROOT);
        require(bytes(treeCid).length > 0, ERROR_EMPTY_TREE_CID);
        require(treeRoot != merkleGate.treeRoot(), ERROR_SAME_TREE_ROOT);
        require(keccak256(bytes(treeCid)) != keccak256(bytes(merkleGate.treeCid())), ERROR_SAME_TREE_CID);
    }
}
