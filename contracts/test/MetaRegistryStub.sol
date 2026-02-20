// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IMetaRegistry.sol";

contract MetaRegistryStub is IMetaRegistry {
    uint256 public override NO_GROUP_ID;
    address public override MODULE;
    address public override STAKING_ROUTER;
    OperatorGroup[] internal groups;

    error InvalidOperatorGroup();
    error InvalidOperatorGroupId();

    event OperatorGroupCreated(uint256 indexed groupId, OperatorGroup groupInfo);
    event OperatorGroupUpdated(uint256 indexed groupId, OperatorGroup groupInfo);
    event OperatorGroupCleared(uint256 indexed groupId);

    constructor() {
        NO_GROUP_ID = 0;
        // Reserve NO_GROUP_ID as a sentinel "no group" entry, like in MetaRegistry.
        groups.push();
    }

    /// @dev Test-only helper to emulate non-zero sentinel values.
    function setNoGroupId(uint256 _noGroupId) external {
        NO_GROUP_ID = _noGroupId;
    }

    /// @dev Test-only helper to force a specific groups length.
    function setGroupsCount(uint256 _groupsCount) external {
        while (groups.length < _groupsCount) {
            groups.push();
        }
        while (groups.length > _groupsCount) {
            groups.pop();
        }
    }

    function setModule(address _module) external {
        MODULE = _module;
    }

    function setStakingRouter(address _stakingRouter) external {
        STAKING_ROUTER = _stakingRouter;
    }

    function getOperatorGroupsCount() external view override returns (uint256) {
        return groups.length;
    }

    function createOrUpdateOperatorGroup(
        uint256 groupId,
        OperatorGroup calldata groupInfo
    ) external override {
        if (groupId >= groups.length) revert InvalidOperatorGroupId();

        if (groupId == NO_GROUP_ID) {
            if (groupInfo.subNodeOperators.length == 0) {
                revert InvalidOperatorGroup();
            }
            groups.push();
            emit OperatorGroupCreated(groups.length - 1, groupInfo);
            return;
        }

        if (groupInfo.subNodeOperators.length == 0) {
            if (groupInfo.externalOperators.length != 0) {
                revert InvalidOperatorGroup();
            }
            emit OperatorGroupCleared(groupId);
            return;
        }

        emit OperatorGroupUpdated(groupId, groupInfo);
    }
}
