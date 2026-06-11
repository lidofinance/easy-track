// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IMetaRegistry.sol";

/// @dev Mirrors the core create/update/reset logic of the real MetaRegistry
///      (feat/add-group-name branch) without production concerns (bond curves,
///      effective weight cache, module address lookups).
contract MetaRegistryStub is IMetaRegistry {
    struct CachedOperatorGroup {
        uint64[] subNodeOperatorIds;
        ExternalOperator[] externalOperators;
    }

    uint256 public override NO_GROUP_ID;
    address public override MODULE;
    address public override STAKING_ROUTER;

    uint256 private groupsCount;
    mapping(uint256 => CachedOperatorGroup) internal groups;
    mapping(uint256 => OperatorGroup) internal groupInfos;
    mapping(uint256 => uint256) internal groupIdByOperatorId;
    mapping(bytes32 => uint256) internal groupIdByExternalKey;

    error InvalidOperatorGroup();
    error InvalidOperatorGroupId();
    error NodeOperatorAlreadyInGroup(uint64 nodeOperatorId);

    event OperatorGroupCreated(uint256 indexed groupId, OperatorGroup groupInfo);
    event OperatorGroupUpdated(uint256 indexed groupId, OperatorGroup groupInfo);
    event OperatorGroupCleared(uint256 indexed groupId);

    constructor() {
        NO_GROUP_ID = 0;
    }

    // ------------------
    // TEST HELPERS
    // ------------------

    function setNoGroupId(uint256 _noGroupId) external {
        NO_GROUP_ID = _noGroupId;
    }

    function setGroupsCount(uint256 _groupsCount) external {
        groupsCount = _groupsCount;
    }

    function setModule(address _module) external {
        MODULE = _module;
    }

    function setStakingRouter(address _stakingRouter) external {
        STAKING_ROUTER = _stakingRouter;
    }

    function setNodeOperatorGroupId(uint256 _nodeOperatorId, uint256 _groupId) external {
        groupIdByOperatorId[_nodeOperatorId] = _groupId;
    }

    function setExternalOperatorGroupId(bytes calldata _data, uint256 _groupId) external {
        groupIdByExternalKey[keccak256(_data)] = _groupId;
    }

    // ------------------
    // IMetaRegistry
    // ------------------

    function getOperatorGroupsCount() external view override returns (uint256) {
        return groupsCount;
    }

    function getNodeOperatorGroupId(uint256 _nodeOperatorId) external view override returns (uint256) {
        return groupIdByOperatorId[_nodeOperatorId];
    }

    function getExternalOperatorGroupId(
        ExternalOperator calldata _externalOperator
    ) external view override returns (uint256) {
        return groupIdByExternalKey[keccak256(_externalOperator.data)];
    }

    function getOperatorGroup(uint256 groupId)
        external
        view
        override
        returns (OperatorGroup memory)
    {
        return groupInfos[groupId];
    }

    function createOrUpdateOperatorGroup(uint256 groupId, OperatorGroup calldata groupInfo)
        external
        override
    {
        if (groupId == NO_GROUP_ID) {
            _createGroup(groupInfo);
        } else {
            _updateGroup(groupId, groupInfo);
        }
    }

    // ------------------
    // INTERNAL (mirrors real MetaRegistry structure)
    // ------------------

    function _createGroup(OperatorGroup calldata groupInfo) internal {
        if (groupInfo.subNodeOperators.length == 0) revert InvalidOperatorGroup();

        uint256 groupId = ++groupsCount;
        _storeGroupData(groupId, groupInfo);
        emit OperatorGroupCreated(groupId, groupInfo);
    }

    function _updateGroup(uint256 groupId, OperatorGroup calldata groupInfo) internal {
        _resetGroup(groupId);

        if (groupInfo.subNodeOperators.length == 0) {
            if (groupInfo.externalOperators.length != 0 || bytes(groupInfo.name).length != 0)
                revert InvalidOperatorGroup();
            emit OperatorGroupCleared(groupId);
        } else {
            _storeGroupData(groupId, groupInfo);
            emit OperatorGroupUpdated(groupId, groupInfo);
        }
    }

    function _resetGroup(uint256 groupId) internal {
        if (groupId > groupsCount) revert InvalidOperatorGroupId();

        CachedOperatorGroup storage group = groups[groupId];

        for (uint256 i; i < group.subNodeOperatorIds.length; ++i) {
            delete groupIdByOperatorId[group.subNodeOperatorIds[i]];
        }
        for (uint256 i; i < group.externalOperators.length; ++i) {
            delete groupIdByExternalKey[keccak256(group.externalOperators[i].data)];
        }

        delete group.subNodeOperatorIds;
        delete group.externalOperators;
        delete groupInfos[groupId];
    }

    function _storeGroupData(uint256 groupId, OperatorGroup calldata groupInfo) internal {
        _storeGroupInfo(groupId, groupInfo);
        _storeSubOperators(groupId, groupInfo.subNodeOperators);
        _storeExternalOperators(groupId, groupInfo.externalOperators);
    }

    function _storeGroupInfo(uint256 groupId, OperatorGroup calldata groupInfo) internal {
        OperatorGroup storage stored = groupInfos[groupId];
        stored.name = groupInfo.name;
        for (uint256 i; i < groupInfo.subNodeOperators.length; ++i) {
            stored.subNodeOperators.push(groupInfo.subNodeOperators[i]);
        }
        for (uint256 i; i < groupInfo.externalOperators.length; ++i) {
            stored.externalOperators.push(groupInfo.externalOperators[i]);
        }
    }

    function _storeSubOperators(uint256 groupId, SubNodeOperator[] calldata ops) internal {
        CachedOperatorGroup storage group = groups[groupId];
        for (uint256 i; i < ops.length; ++i) {
            uint64 noId = ops[i].nodeOperatorId;
            if (groupIdByOperatorId[noId] != NO_GROUP_ID) revert NodeOperatorAlreadyInGroup(noId);
            groupIdByOperatorId[noId] = groupId;
            group.subNodeOperatorIds.push(noId);
        }
    }

    function _storeExternalOperators(uint256 groupId, ExternalOperator[] calldata ops) internal {
        CachedOperatorGroup storage group = groups[groupId];
        for (uint256 i; i < ops.length; ++i) {
            bytes32 key = keccak256(ops[i].data);
            groupIdByExternalKey[key] = groupId;
            group.externalOperators.push(ops[i]);
        }
    }
}
