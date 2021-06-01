// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "./EasyTrackExecutor.sol";

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

contract NodeOperatorsEasyTrackExecutor is EasyTrackExecutor {
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

    NodeOperatorsRegistry public nodeOperatorsRegistry;

    constructor(address _easyTracksRegistry, address _nodeOperatorsRegistry)
        EasyTrackExecutor(_easyTracksRegistry)
    {
        nodeOperatorsRegistry = NodeOperatorsRegistry(_nodeOperatorsRegistry);
    }

    function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal view override {
        (uint256 _nodeOperatorId, uint256 _stakingLimit) = _decodeMotionData(_data);

        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(_nodeOperatorId);
        _validateCallerIsRewardAddress(_caller, nodeOperatorData);
        _validateNodeOperatorData(nodeOperatorData, _stakingLimit);
    }

    function _beforeCancelMotionGuard(
        address _caller,
        bytes memory _motionData,
        bytes memory _cancelData
    ) internal view override {
        uint256 _nodeOperatorId = abi.decode(_cancelData, (uint256));
        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(_nodeOperatorId);
        _validateCallerIsRewardAddress(_caller, nodeOperatorData);
    }

    function execute(bytes memory _motionData, bytes memory _enactData) external override {
        (uint256 _nodeOperatorId, uint256 _stakingLimit) = _decodeMotionData(_motionData);

        NodeOperatorData memory nodeOperatorData = _getNodeOperatorData(_nodeOperatorId);
        _validateNodeOperatorData(nodeOperatorData, _stakingLimit);

        nodeOperatorsRegistry.setNodeOperatorStakingLimit(_nodeOperatorId, uint64(_stakingLimit));
    }

    function _validateCallerIsRewardAddress(
        address _caller,
        NodeOperatorData memory _nodeOperatorData
    ) private pure {
        require(_nodeOperatorData.rewardAddress == _caller, ERROR_CALLER_IS_NOT_NODE_OPERATOR);
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

    function _decodeMotionData(bytes memory _motionData)
        public
        pure
        returns (uint256 _nodeOperatorId, uint256 _stakingLimit)
    {
        (_nodeOperatorId, _stakingLimit) = abi.decode(_motionData, (uint256, uint256));
    }
}
