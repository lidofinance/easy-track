// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IMetaRegistry.sol";

contract MetaRegistryStub is IMetaRegistry {
    uint256 public override NO_GROUP_ID;
    address public override MODULE;
    address public override STAKING_ROUTER;
    uint256 private groupsCount;
    mapping(uint256 => OperatorGroup) internal groups;
    mapping(uint256 => uint256) internal nodeOperatorGroupIdById;
    mapping(bytes32 => uint256) internal externalOperatorGroupIdByKey;

    error InvalidOperatorGroup();
    error InvalidOperatorGroupId();

    event OperatorGroupCreated(uint256 indexed groupId, OperatorGroup groupInfo);
    event OperatorGroupUpdated(uint256 indexed groupId, OperatorGroup groupInfo);
    event OperatorGroupCleared(uint256 indexed groupId);

    constructor() {
        NO_GROUP_ID = 0;
    }

    /// @dev Test-only helper to emulate non-zero sentinel values.
    function setNoGroupId(uint256 _noGroupId) external {
        NO_GROUP_ID = _noGroupId;
    }

    /// @dev Test-only helper to force a specific groups count.
    function setGroupsCount(uint256 _groupsCount) external {
        groupsCount = _groupsCount;
    }

    function setModule(address _module) external {
        MODULE = _module;
    }

    function setStakingRouter(address _stakingRouter) external {
        STAKING_ROUTER = _stakingRouter;
    }

    function setNodeOperatorGroupId(
        uint256 _nodeOperatorId,
        uint256 _groupId
    ) external {
        nodeOperatorGroupIdById[_nodeOperatorId] = _groupId;
    }

    function setExternalOperatorGroupId(
        bytes calldata _externalOperatorData,
        uint256 _groupId
    ) external {
        externalOperatorGroupIdByKey[
            keccak256(_externalOperatorData)
        ] = _groupId;
    }

    function getOperatorGroupsCount() external view override returns (uint256) {
        return groupsCount;
    }

    function getNodeOperatorGroupId(
        uint256 _nodeOperatorId
    ) external view override returns (uint256) {
        return nodeOperatorGroupIdById[_nodeOperatorId];
    }

    function getExternalOperatorGroupId(
        ExternalOperator calldata _externalOperator
    ) external view override returns (uint256) {
        return externalOperatorGroupIdByKey[
            keccak256(_externalOperator.data)
        ];
    }

    function createOrUpdateOperatorGroup(
        uint256 groupId,
        OperatorGroup calldata groupInfo
    ) external override {
        if (groupId == NO_GROUP_ID) {
            if (groupInfo.subNodeOperators.length == 0) {
                revert InvalidOperatorGroup();
            }
            groupsCount++;
            emit OperatorGroupCreated(groupsCount, groupInfo);
            return;
        }

        if (groupId > groupsCount) revert InvalidOperatorGroupId();

        if (groupInfo.subNodeOperators.length == 0) {
            if (groupInfo.externalOperators.length != 0 || bytes(groupInfo.name).length != 0) {
                revert InvalidOperatorGroup();
            }
            emit OperatorGroupCleared(groupId);
            return;
        }

        emit OperatorGroupUpdated(groupId, groupInfo);
    }
}
