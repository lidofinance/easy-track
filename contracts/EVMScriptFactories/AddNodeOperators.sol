// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function addNodeOperator(
        string memory _name,
        address _rewardAddress
    ) external returns (uint256 id);
}

/// @notice Creates EVMScript to add new batch of node operators
contract AddNodeOperators is TrustedCaller, IEVMScriptFactory {
    struct NodeOperator {
        string name;
        address rewardAddress;

    }

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _nodeOperatorsRegistry
    ) TrustedCaller(_trustedCaller) {
        nodeOperatorsRegistry = INodeOperatorsRegistry(_nodeOperatorsRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        NodeOperator[] memory decodedCallData = abi.decode(_evmScriptCallData, (NodeOperator[]));
        bytes[] memory nodeOperatorsCallData = new bytes[](decodedCallData.length);

        for (uint i = 0; i < decodedCallData.length; i++) {
            nodeOperatorsCallData[i] = abi.encode(decodedCallData[i].name, decodedCallData[i].rewardAddress);
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.addNodeOperator.selector,
                nodeOperatorsCallData
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (NodeOperator[] memory nodeOperators) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (NodeOperator[] memory nodeOperators) {
        nodeOperators = abi.decode(_evmScriptCallData, (NodeOperator[]));
    }
}
