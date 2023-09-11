// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

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
contract IncreaseNodeOperatorStakingLimitWithManager is IEVMScriptFactory {
    struct NodeOperatorData {
        uint256 id;
        bool active;
        address rewardAddress;
        uint256 stakingLimit;
        uint256 totalSigningKeys;
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

    constructor(address _nodeOperatorsRegistry) {
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
    ) external view override returns (bytes memory) {
        _validateCreatorAndEVMScriptCallData(_creator, _evmScriptCallData);
        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.setNodeOperatorStakingLimit.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (uint256 _nodeOperatorId, uint256 _stakingLimit) where
    /// _nodeOperatorId - id of node operator in NodeOperatorsRegistry
    /// _stakingLimit - new staking limit
    /// @return _nodeOperatorId Id of node operator in NodeOperatorsRegistry
    /// @return _stakingLimit New staking limit
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (uint256 _nodeOperatorId, uint256 _stakingLimit) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (uint256 _nodeOperatorId, uint256 _stakingLimit) {
        (_nodeOperatorId, _stakingLimit) = abi.decode(_evmScriptCallData, (uint256, uint256));
    }

    function _validateCreatorAndEVMScriptCallData(
        address _creator,
        bytes memory _evmScriptCallData
    ) private view {
        (uint256 _nodeOperatorId, uint256 _stakingLimit) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(_nodeOperatorId);
        uint256[] memory role_params = new uint256[](1);
        role_params[0] = _nodeOperatorId;

        require(
            _creator == nodeOperatorData.rewardAddress ||
                nodeOperatorsRegistry.canPerform(_creator, MANAGE_SIGNING_KEYS_ROLE, role_params),
            ERROR_CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER
        );
        require(nodeOperatorData.active, ERROR_NODE_OPERATOR_DISABLED);
        require(nodeOperatorData.stakingLimit < _stakingLimit, ERROR_STAKING_LIMIT_TOO_LOW);
        require(nodeOperatorData.totalSigningKeys >= _stakingLimit, ERROR_NOT_ENOUGH_SIGNING_KEYS);
    }

    function _getNodeOperatorData(
        uint256 _nodeOperatorId
    ) private view returns (NodeOperatorData memory _nodeOperatorData) {
        (
            bool active,
            ,
            address rewardAddress,
            uint64 stakingLimit,
            ,
            uint64 totalSigningKeys,

        ) = nodeOperatorsRegistry.getNodeOperator(_nodeOperatorId, false);

        _nodeOperatorData.id = _nodeOperatorId;
        _nodeOperatorData.active = active;
        _nodeOperatorData.rewardAddress = rewardAddress;
        _nodeOperatorData.stakingLimit = stakingLimit;
        _nodeOperatorData.totalSigningKeys = totalSigningKeys;
    }
}
