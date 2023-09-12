// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function getNodeOperator(
        uint256 _id,
        bool _fullInfo
    )
        external
        view
        returns (
            bool active,
            string memory name,
            address rewardAddress,
            uint64 stakingLimit,
            uint64 stoppedValidators,
            uint64 totalSigningKeys,
            uint64 usedSigningKeys
        );

    function canPerform(
        address _sender,
        bytes32 _role,
        uint256[] memory _params
    ) external view returns (bool);

    function setNodeOperatorStakingLimit(uint256 _id, uint64 _stakingLimit) external;
}

/// @author psirex
/// @notice Creates EVMScript to increase staking limit for node operator
contract IncreaseNodeOperatorsStakingLimitByCommitee is TrustedCaller, IEVMScriptFactory {
    struct NodeOperatorData {
        uint256 id;
        bool active;
        address rewardAddress;
        uint256 stakingLimit;
        uint256 totalSigningKeys;
    }

    struct StakingLimitData {
        uint256 nodeOperatorId;
        uint256 stakingLimit;
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

    string private constant ERROR_NODE_OPERATOR_DISABLED = "NODE_OPERATOR_DISABLED";
    string private constant ERROR_CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER =
        "CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER";
    string private constant ERROR_STAKING_LIMIT_TOO_LOW = "STAKING_LIMIT_TOO_LOW";
    string private constant ERROR_NOT_ENOUGH_SIGNING_KEYS = "NOT_ENOUGH_SIGNING_KEYS";

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
        StakingLimitData[] memory decodedCallData = abi.decode(
            _evmScriptCallData,
            (StakingLimitData[])
        );
        bytes[] memory stakingLimitCalldata = new bytes[](decodedCallData.length);

        for (uint i = 0; i < decodedCallData.length; i++) {
            _validateEVMScriptCallData(decodedCallData[i]);
            stakingLimitCalldata[i] = abi.encode(decodedCallData[i]);
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.setNodeOperatorStakingLimit.selector,
                stakingLimitCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (StakingLimitData[]) 
    /// @return stakingLimit array of StakingLimitData struct
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (StakingLimitData[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (StakingLimitData[] memory) {
        return abi.decode(_evmScriptCallData, (StakingLimitData[]));
    }

    function _validateEVMScriptCallData(StakingLimitData memory stakingLimitData) private view {
        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(
            stakingLimitData.nodeOperatorId
        );

        require(nodeOperatorData.active, ERROR_NODE_OPERATOR_DISABLED);
        require(
            nodeOperatorData.stakingLimit < stakingLimitData.stakingLimit,
            ERROR_STAKING_LIMIT_TOO_LOW
        );
        require(
            nodeOperatorData.totalSigningKeys >= stakingLimitData.stakingLimit,
            ERROR_NOT_ENOUGH_SIGNING_KEYS
        );
    }

    function _getNodeOperatorData(
        uint256 _nodeOperatorId
    ) private view returns (NodeOperatorData memory _nodeOperatorData) {
        (
            bool active,
            ,
            ,
            uint64 stakingLimit,
            ,
            uint64 totalSigningKeys,

        ) = nodeOperatorsRegistry.getNodeOperator(_nodeOperatorId, false);

        _nodeOperatorData.id = _nodeOperatorId;
        _nodeOperatorData.active = active;
        _nodeOperatorData.stakingLimit = stakingLimit;
        _nodeOperatorData.totalSigningKeys = totalSigningKeys;
    }
}
