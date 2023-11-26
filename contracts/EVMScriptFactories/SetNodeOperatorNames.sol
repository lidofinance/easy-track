// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorRegestry.sol";

/// @notice Creates EVMScript to set name of several node operators
contract SetNodeOperatorNames is TrustedCaller, IEVMScriptFactory {
    struct SetNameInput {
        uint256 nodeOperatorId;
        string name;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant ERROR_WRONG_NAME_LENGTH = "WRONG_NAME_LENGTH";
    string private constant ERROR_SAME_NAME = "SAME_NAME";
    string private constant ERROR_NODE_OPERATORS_IS_NOT_SORTED = "NODE_OPERATORS_IS_NOT_SORTED";
    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";

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

    /// @notice Creates EVMScript to set name of several node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (SetNameInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        SetNameInput[] memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(decodedCallData);

        bytes[] memory nodeOperatorsNamesCalldata = new bytes[](decodedCallData.length);

        for (uint256 i = 0; i < decodedCallData.length; i++) {
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

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (SetNameInput[])
    /// @return SetNameInput[]
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

    function _validateInputData(SetNameInput[] memory _decodedCallData) private view {
        uint256 maxNameLength = nodeOperatorsRegistry.MAX_NODE_OPERATOR_NAME_LENGTH();
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        require(_decodedCallData.length > 0, ERROR_EMPTY_CALLDATA);
        require(
            _decodedCallData[_decodedCallData.length - 1].nodeOperatorId < nodeOperatorsCount,
            ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE
        );

        for (uint256 i = 0; i < _decodedCallData.length; i++) {
            require(
                i == 0 ||
                    _decodedCallData[i].nodeOperatorId > _decodedCallData[i - 1].nodeOperatorId,
                ERROR_NODE_OPERATORS_IS_NOT_SORTED
            );
            require(
                bytes(_decodedCallData[i].name).length > 0 &&
                    bytes(_decodedCallData[i].name).length <= maxNameLength,
                ERROR_WRONG_NAME_LENGTH
            );

            (
                /* bool active */,
                string memory name,
                /* address rewardAddress */,
                /* uint64 stakingLimit */,
                /* uint64 stoppedValidators */,
                /* uint64 totalSigningKeys */,
                /* uint64 usedSigningKeys */
            ) = nodeOperatorsRegistry.getNodeOperator(
                _decodedCallData[i].nodeOperatorId,
                true
            );
            nodeOperatorsRegistry.getNodeOperator(_decodedCallData[i].nodeOperatorId, true);
            nodeOperatorsRegistry.getNodeOperator(_decodedCallData[i].nodeOperatorId, true);
            require(
                keccak256(bytes(_decodedCallData[i].name)) != keccak256(bytes(name)),
                ERROR_SAME_NAME
            );
        }
    }
}
