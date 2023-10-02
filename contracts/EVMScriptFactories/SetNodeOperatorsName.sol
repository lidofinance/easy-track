// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorRegestry.sol";

/// @notice Creates EVMScript to set node operators name
contract SetNodeOperatorNames is TrustedCaller, IEVMScriptFactory {
    struct SetNameInput {
        uint256 nodeOperatorId;
        string name;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant NODE_OPERATOR_INDEX_OUT_OF_RANGE = "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant WRONG_NAME_LENGTH = "WRONG_NAME_LENGTH";
    string private constant SAME_NAME = "SAME_NAME";

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
        SetNameInput[] memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(decodedCallData);

        bytes[] memory nodeOperatorsNamesCalldata = new bytes[](decodedCallData.length);

        for (uint i = 0; i < decodedCallData.length; i++) {
            nodeOperatorsNamesCalldata[i] = abi.encode(
                decodedCallData[i].nodeOperatorId,
                decodedCallData[i].name
            );
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.setNodeOperatorName.selector,
                nodeOperatorsNamesCalldata
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (SetNameInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (SetNameInput[] memory) {
        return abi.decode(_evmScriptCallData, (SetNameInput[]));
    }

    function _validateInputData(SetNameInput[] memory _nodeOperatorNamesInput) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint i = 0; i < _nodeOperatorNamesInput.length; i++) {
            require(
                _nodeOperatorNamesInput[i].nodeOperatorId < nodeOperatorsCount,
                NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );

            require(
                bytes(_nodeOperatorNamesInput[i].name).length > 0 &&
                    bytes(_nodeOperatorNamesInput[i].name).length <=
                    nodeOperatorsRegistry.MAX_NODE_OPERATOR_NAME_LENGTH(),
                WRONG_NAME_LENGTH
            );

            (
                /* bool active */,
                string memory name,
                /* address rewardAddress */,
                /* uint64 stakingLimit */,
                /* uint64 stoppedValidators */,
                /* uint64 totalSigningKeys */,
                /* uint64 usedSigningKeys */
            ) = nodeOperatorsRegistry.getNodeOperator(_nodeOperatorNamesInput[i].nodeOperatorId, true);

            require(keccak256(bytes(_nodeOperatorNamesInput[i].name)) != keccak256(bytes(name)), SAME_NAME);
        }
    }
}
