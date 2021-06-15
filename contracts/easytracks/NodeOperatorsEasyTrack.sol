// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../MotionsRegistry.sol";

interface NodeOperatorsRegistry {
    function getNodeOperator(uint256 _id, bool _fullInfo)
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

    function setNodeOperatorStakingLimit(uint256 _id, uint64 _stakingLimit) external;
}

contract NodeOperatorsEasyTrack {
    struct NodeOperatorData {
        bool active;
        address rewardAddress;
        uint256 stakingLimit;
        uint256 totalSigningKeys;
    }

    string private constant ERROR_NODE_OPERATOR_DISABLED = "NODE_OPERATOR_DISABLED";
    string private constant ERROR_CALLER_IS_NOT_NODE_OPERATOR = "CALLER_IS_NOT_NODE_OPERATOR";
    string private constant ERROR_STAKING_LIMIT_TOO_LOW = "STAKING_LIMIT_TOO_LOW";
    string private constant ERROR_NOT_ENOUGH_SIGNING_KEYS = "NOT_ENOUGH_SIGNING_KEYS";

    MotionsRegistry public motionsRegistry;
    NodeOperatorsRegistry public nodeOperatorsRegistry;

    constructor(MotionsRegistry _motionsRegistry, address _nodeOperatorsRegistry) {
        motionsRegistry = _motionsRegistry;
        nodeOperatorsRegistry = NodeOperatorsRegistry(_nodeOperatorsRegistry);
    }

    function createMotion(uint256 _nodeOperatorId, uint256 _stakingLimit)
        external
        returns (uint256)
    {
        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(_nodeOperatorId);
        _validateSenderIsRewardAddress(nodeOperatorData);
        _validateNodeOperatorData(nodeOperatorData, _stakingLimit);
        return motionsRegistry.createMotion(_encodeMotionData(_nodeOperatorId, _stakingLimit));
    }

    function cancelMotion(uint256 _motionId, uint256 _nodeOperatorId) external {
        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(_nodeOperatorId);
        _validateSenderIsRewardAddress(nodeOperatorData);
        motionsRegistry.cancelMotion(_motionId);
    }

    function enactMotion(uint256 _motionId) external {
        bytes memory motionData = motionsRegistry.getMotionData(_motionId);
        (uint256 _nodeOperatorId, uint256 _stakingLimit) = _decodeMotionData(motionData);
        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(_nodeOperatorId);
        _validateNodeOperatorData(nodeOperatorData, _stakingLimit);
        motionsRegistry.enactMotion(
            _motionId,
            motionsRegistry.createEvmScript(
                address(nodeOperatorsRegistry),
                abi.encodeWithSelector(
                    nodeOperatorsRegistry.setNodeOperatorStakingLimit.selector,
                    _nodeOperatorId,
                    _stakingLimit
                )
            )
        );
    }

    function _validateSenderIsRewardAddress(NodeOperatorData memory _nodeOperatorData)
        private
        view
    {
        require(_nodeOperatorData.rewardAddress == msg.sender, ERROR_CALLER_IS_NOT_NODE_OPERATOR);
    }

    function _validateNodeOperatorData(
        NodeOperatorData memory _nodeOperatorData,
        uint256 _stakingLimit
    ) private pure {
        require(_nodeOperatorData.active, ERROR_NODE_OPERATOR_DISABLED);
        require(_nodeOperatorData.stakingLimit < _stakingLimit, ERROR_STAKING_LIMIT_TOO_LOW);
        require(_nodeOperatorData.totalSigningKeys >= _stakingLimit, ERROR_NOT_ENOUGH_SIGNING_KEYS);
    }

    function _getNodeOperatorData(uint256 _nodeOperatorId)
        private
        view
        returns (NodeOperatorData memory _nodeOperatorData)
    {
        (bool active, , address rewardAddress, uint64 stakingLimit, , uint64 totalSigningKeys, ) =
            nodeOperatorsRegistry.getNodeOperator(_nodeOperatorId, false);

        _nodeOperatorData.active = active;
        _nodeOperatorData.rewardAddress = rewardAddress;
        _nodeOperatorData.stakingLimit = stakingLimit;
        _nodeOperatorData.totalSigningKeys = totalSigningKeys;
    }

    function _encodeMotionData(uint256 _nodeOperatorId, uint256 _stakingLimit)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(_nodeOperatorId, _stakingLimit);
    }

    function _decodeMotionData(bytes memory _motionData)
        public
        pure
        returns (uint256 _nodeOperatorId, uint256 _stakingLimit)
    {
        (_nodeOperatorId, _stakingLimit) = abi.decode(_motionData, (uint256, uint256));
    }
}
