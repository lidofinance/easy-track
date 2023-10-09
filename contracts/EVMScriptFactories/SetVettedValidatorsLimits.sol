// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorRegestry.sol";

/// @notice Creates EVMScript to increase staking limit for node operator
contract SetVettedValidatorsLimits is TrustedCaller, IEVMScriptFactory {
    struct VettedValidatorsLimitInput {
        uint256 nodeOperatorId;
        uint256 stakingLimit;
    }

    struct NodeOperatorData {
        uint256 id;
        uint64 totalSigningKeys;
    }

    // -------------
    // CONSTANTS
    // -------------
    /// @notice keccak256("MANAGE_SIGNING_KEYS")
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE =
        0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee;

    // -------------
    // ERRORS
    // -------------

    string private constant NOT_ENOUGH_SIGNING_KEYS = "NOT_ENOUGH_SIGNING_KEYS";
    string private constant NODE_OPERATOR_INDEX_OUT_OF_RANGE = "NODE_OPERATOR_INDEX_OUT_OF_RANGE";

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

    /// @notice Creates EVMScript to increase staking limit for node operator
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (uint256 _nodeOperatorId, uint256 _stakingLimit) where
    /// _nodeOperatorId - id of node operator in NodeOperatorsRegistry
    /// _stakingLimit - new staking limit
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        VettedValidatorsLimitInput[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        _validateInputData(decodedCallData);
        
        bytes[] memory setVettedValidatorsLimitsCalldata = new bytes[](decodedCallData.length);

        for (uint256 i = 0; i < decodedCallData.length; i++) {
            setVettedValidatorsLimitsCalldata[i] = abi.encode(
                decodedCallData[i].nodeOperatorId,
                decodedCallData[i].stakingLimit
            );
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.setNodeOperatorStakingLimit.selector,
                setVettedValidatorsLimitsCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (uint256 _nodeOperatorId, uint256 _stakingLimit) where
    /// _nodeOperatorId - id of node operator in NodeOperatorsRegistry
    /// _stakingLimit - new staking limit
    /// @return VettedValidatorsLimitInput
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (VettedValidatorsLimitInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (VettedValidatorsLimitInput[] memory) {
        return abi.decode(_evmScriptCallData, (VettedValidatorsLimitInput[]));
    }

    function _validateInputData(VettedValidatorsLimitInput[] memory _decodedCallData) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint256 i = 0; i < _decodedCallData.length; i++) {
            require(
                _decodedCallData[i].nodeOperatorId < nodeOperatorsCount,
                NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );

            NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(
                _decodedCallData[i].nodeOperatorId
            );

            require(
                nodeOperatorData.totalSigningKeys >= _decodedCallData[i].stakingLimit,
                NOT_ENOUGH_SIGNING_KEYS
            );
        }
    }

    function _getNodeOperatorData(
        uint256 _nodeOperatorId
    ) private view returns (NodeOperatorData memory _nodeOperatorData) {
        (
            /* bool active */,
            /* string memory name */,
            /* address rewardAddress */,
            /* uint64 stakingLimit */,
            /* uint64 stoppedValidators */,
            uint64 totalSigningKeys,
            /* uint64 usedSigningKeys */
        ) = nodeOperatorsRegistry.getNodeOperator(_nodeOperatorId, false);

        _nodeOperatorData.id = _nodeOperatorId;
        _nodeOperatorData.totalSigningKeys = totalSigningKeys;
    }
}
