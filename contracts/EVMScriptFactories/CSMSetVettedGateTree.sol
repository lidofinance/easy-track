// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IVettedGate.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to set tree for CSM's VettedGate 
contract CSMSetVettedGateTree is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_TREE_ROOT =
        "EMPTY_TREE_ROOT";
    string private constant ERROR_TREE_CID =
        "EMPTY_TREE_CID";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Alias for factory (e.g. "IdentifiedCommunityStakerSetTreeParams")
    string public name;

    /// @notice Address of VettedGate
    IVettedGate public immutable vettedGate;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, string memory _name, address _vettedGate)
        TrustedCaller(_trustedCaller)
    {
        name = _name;
        vettedGate = IVettedGate(_vettedGate);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to settle EL stealing penalty for the specific node operators on CSM
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
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
                address(vettedGate),
                IVettedGate.setTreeParams.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds
    /// @return Node operator IDs to settle EL stealing penalty
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32, string memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32, string memory)
    {
        return abi.decode(_evmScriptCallData, (bytes32, string));
    }

    function _validateInputData(
        bytes32 treeRoot,
        string memory treeCid
    ) private pure {
        require(treeRoot != bytes32(0), ERROR_TREE_ROOT);
        require(bytes(treeCid).length > 0, ERROR_TREE_CID);
    }
}
