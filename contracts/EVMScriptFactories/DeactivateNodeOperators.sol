// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function deactivateNodeOperator(uint256 _nodeOperatorId) external;

    function getNodeOperatorIsActive(uint256 _nodeOperatorId) external view returns (bool);

    function getNodeOperatorsCount() external view returns (uint256);
}

/// @notice Creates EVMScript to deactivate several node operator
contract DeactivateNodeOperators is TrustedCaller, IEVMScriptFactory {
    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;

    // -------------
    // ERRORS
    // -------------

    string private constant WRONG_OPERATOR_ACTIVE_STATE = "WRONG_OPERATOR_ACTIVE_STATE";
    string private constant NODE_OPERATOR_INDEX_OUT_OF_RANGE = "NODE_OPERATOR_INDEX_OUT_OF_RANGE";

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
        uint256[] memory decodedCallData = abi.decode(_evmScriptCallData, (uint256[]));
        bytes[] memory nodeOperatorsIdsCalldata = new bytes[](decodedCallData.length);

        _validateInputData(decodedCallData);

        for (uint i = 0; i < decodedCallData.length; i++) {
            nodeOperatorsIdsCalldata[i] = abi.encode(decodedCallData[i]);
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.deactivateNodeOperator.selector,
                nodeOperatorsIdsCalldata
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (uint256[] memory nodeOperatorIds) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (uint256[] memory nodeOperatorIds) {
        return abi.decode(_evmScriptCallData, (uint256[]));
    }

    function _validateInputData(uint256[] memory _nodeOperatorIds) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint i = 0; i < _nodeOperatorIds.length; i++) {
            require(_nodeOperatorIds[i] < nodeOperatorsCount, NODE_OPERATOR_INDEX_OUT_OF_RANGE);
            require(
                nodeOperatorsRegistry.getNodeOperatorIsActive(_nodeOperatorIds[i]) == true,
                WRONG_OPERATOR_ACTIVE_STATE
            );
        }
    }
}
