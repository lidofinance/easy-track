// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import {
    IMetaRegistry,
    IBaseModule,
    IStakingRouter,
    INodeOperatorsRegistry,
    NodeOperatorManagementProperties
} from "../../interfaces/External.sol";
import { ICreateOrUpdateOperatorGroup } from "../../interfaces/Factories.sol";

/// @notice Deployed `CreateOrUpdateOperatorGroup:CM` (deployed-sm-<chain>.json): a motion creates a new
///         MetaRegistry operator group, updates an existing one, or empties it.
contract CreateOrUpdateOperatorGroupScenario is EasyTrackScenarioBase {
    ICreateOrUpdateOperatorGroup internal factory;
    IMetaRegistry internal metaRegistry;
    IBaseModule internal module;
    INodeOperatorsRegistry internal externalModule;
    uint256 internal externalModuleId;

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        factory = ICreateOrUpdateOperatorGroup(_factoryAddress(cfg.smArtifact, "CreateOrUpdateOperatorGroup:CM"));
        metaRegistry = IMetaRegistry(factory.metaRegistry());
        module = IBaseModule(factory.module());
        IStakingRouter router = IStakingRouter(factory.stakingRouter());
        externalModuleId = factory.allowedExternalModuleId();
        externalModule = INodeOperatorsRegistry(router.getStakingModule(externalModuleId).stakingModuleAddress);
        subject = address(factory);
        creator = factory.trustedCaller();
    }

    function test_createsOperatorGroup() external onlyForked {
        (uint64 subOperator, uint64 externalOperator) = _givenGroupMembers();
        uint256 groupsBefore = metaRegistry.getOperatorGroupsCount();

        enact(_encodeNewGroup(subOperator, externalOperator));

        uint256 newGroupId = metaRegistry.getOperatorGroupsCount();
        assertEq(newGroupId, groupsBefore + 1, "operator group not created");
        // both members now resolve to the new group
        assertEq(metaRegistry.getNodeOperatorGroupId(subOperator), newGroupId, "sub operator not in group");
        assertEq(_externalOperatorGroupId(externalOperator), newGroupId, "external operator not in group");
    }

    function test_updatesOperatorGroupToNonEmpty() external onlyForked {
        // A group with only the sub operator; the motion updates it to also include the external operator.
        (uint256 groupId, IMetaRegistry.OperatorGroup memory current, uint64 subOperator, uint64 externalOperator) =
            _givenExistingGroup(false);
        assertEq(_externalOperatorGroupId(externalOperator), metaRegistry.NO_GROUP_ID(), "setup: external already grouped");

        IMetaRegistry.SubNodeOperator[] memory subs = new IMetaRegistry.SubNodeOperator[](1);
        subs[0] = IMetaRegistry.SubNodeOperator({ nodeOperatorId: subOperator, share: 10000 });
        IMetaRegistry.ExternalOperator[] memory exts = new IMetaRegistry.ExternalOperator[](1);
        exts[0] = _ext(externalOperator);
        IMetaRegistry.OperatorGroup memory updated =
            IMetaRegistry.OperatorGroup({ name: "updated-group", subNodeOperators: subs, externalOperators: exts });

        enact(abi.encode(groupId, current, updated));

        IMetaRegistry.OperatorGroup memory onchain = metaRegistry.getOperatorGroup(groupId);
        assertEq(onchain.externalOperators.length, 1, "external operator not added");
        assertEq(_externalOperatorGroupId(externalOperator), groupId, "external operator not in group");
        assertEq(metaRegistry.getNodeOperatorGroupId(subOperator), groupId, "sub operator dropped");
    }

    function test_updatesOperatorGroupToEmpty() external onlyForked {
        // A group with a sub + external operator; the motion empties it (frees both members).
        (uint256 groupId, IMetaRegistry.OperatorGroup memory current, uint64 subOperator, uint64 externalOperator) =
            _givenExistingGroup(true);
        assertEq(metaRegistry.getNodeOperatorGroupId(subOperator), groupId, "setup: sub not grouped");

        IMetaRegistry.OperatorGroup memory empty; // name "", no sub/external operators

        enact(abi.encode(groupId, current, empty));

        assertEq(metaRegistry.getNodeOperatorGroupId(subOperator), metaRegistry.NO_GROUP_ID(), "sub still grouped");
        assertEq(_externalOperatorGroupId(externalOperator), metaRegistry.NO_GROUP_ID(), "external still grouped");
    }

    function test_updatesEmptyGroupToEmpty() external onlyForked {
        (uint256 groupId, IMetaRegistry.OperatorGroup memory current, uint64 subOperator,) = _givenExistingGroup(true);
        IMetaRegistry.OperatorGroup memory empty;

        // Empty the group, then apply an empty -> empty update (a no-op that must still validate/enact).
        enact(abi.encode(groupId, current, empty));
        IMetaRegistry.OperatorGroup memory nowEmpty = metaRegistry.getOperatorGroup(groupId);
        enact(abi.encode(groupId, nowEmpty, empty));

        assertEq(metaRegistry.getNodeOperatorGroupId(subOperator), metaRegistry.NO_GROUP_ID(), "sub grouped after empty->empty");
    }

    function test_revertsWhenCurrentGroupChangesBeforeEnact() external onlyForked {
        (uint256 groupId, IMetaRegistry.OperatorGroup memory current, uint64 subOperator, uint64 externalOperator) =
            _givenExistingGroup(false);

        IMetaRegistry.SubNodeOperator[] memory subs = new IMetaRegistry.SubNodeOperator[](1);
        subs[0] = IMetaRegistry.SubNodeOperator({ nodeOperatorId: subOperator, share: 10000 });
        IMetaRegistry.ExternalOperator[] memory exts = new IMetaRegistry.ExternalOperator[](1);
        exts[0] = _ext(externalOperator);
        // an update motion committed to the current (sub-only) group definition
        bytes memory callData = abi.encode(
            groupId,
            current,
            IMetaRegistry.OperatorGroup({ name: "updated-group", subNodeOperators: subs, externalOperators: exts })
        );

        vm.prank(creator);
        uint256 motionId = easyTrack.createMotion(subject, callData);

        // rename the group so the committed `currentGroupInfo` no longer matches
        metaRegistry.createOrUpdateOperatorGroup(
            groupId,
            IMetaRegistry.OperatorGroup({
                name: "changed-name",
                subNodeOperators: subs,
                externalOperators: new IMetaRegistry.ExternalOperator[](0)
            })
        );

        vm.warp(block.timestamp + easyTrack.motionDuration() + 1);
        vm.prank(makeAddr("stranger"));
        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        easyTrack.enactMotion(motionId, callData);
    }

    // --- scenario helpers ---

    /// @dev A fresh curated (sub) operator and a fresh legacy-NOR (external) operator.
    function _givenGroupMembers() private returns (uint64 subOperator, uint64 externalOperator) {
        _grantRole(address(module), "CREATE_NODE_OPERATOR_ROLE", address(this));
        address subAddr = makeAddr("cm-sub-operator");
        subOperator =
            uint64(module.createNodeOperator(subAddr, NodeOperatorManagementProperties(subAddr, subAddr, false), address(0)));

        vm.prank(cfg.agent);
        externalOperator = uint64(externalModule.addNodeOperator("scenario-external", makeAddr("nor-external-reward")));
    }

    /// @dev Create a group directly via MetaRegistry (data prep) and return its id + current definition
    ///      (the commit the update motion must match). `withExternal` adds the external operator too.
    function _givenExistingGroup(bool withExternal)
        private
        returns (uint256 groupId, IMetaRegistry.OperatorGroup memory current, uint64 subOperator, uint64 externalOperator)
    {
        (subOperator, externalOperator) = _givenGroupMembers();
        _grantRole(address(metaRegistry), "MANAGE_OPERATOR_GROUPS_ROLE", address(this));

        IMetaRegistry.SubNodeOperator[] memory subs = new IMetaRegistry.SubNodeOperator[](1);
        subs[0] = IMetaRegistry.SubNodeOperator({ nodeOperatorId: subOperator, share: 10000 });
        IMetaRegistry.ExternalOperator[] memory exts = new IMetaRegistry.ExternalOperator[](withExternal ? 1 : 0);
        if (withExternal) exts[0] = _ext(externalOperator);

        metaRegistry.createOrUpdateOperatorGroup(
            metaRegistry.NO_GROUP_ID(),
            IMetaRegistry.OperatorGroup({ name: "initial-group", subNodeOperators: subs, externalOperators: exts })
        );
        groupId = metaRegistry.getNodeOperatorGroupId(subOperator);
        current = metaRegistry.getOperatorGroup(groupId);
    }

    function _encodeNewGroup(uint64 subOperator, uint64 externalOperator) private view returns (bytes memory) {
        IMetaRegistry.SubNodeOperator[] memory subs = new IMetaRegistry.SubNodeOperator[](1);
        subs[0] = IMetaRegistry.SubNodeOperator({ nodeOperatorId: subOperator, share: 10000 });

        IMetaRegistry.ExternalOperator[] memory exts = new IMetaRegistry.ExternalOperator[](1);
        exts[0] = _ext(externalOperator);

        IMetaRegistry.OperatorGroup memory newGroup =
            IMetaRegistry.OperatorGroup({ name: "scenario-group", subNodeOperators: subs, externalOperators: exts });
        IMetaRegistry.OperatorGroup memory currentEmpty;
        return abi.encode(metaRegistry.NO_GROUP_ID(), currentEmpty, newGroup);
    }

    function _ext(uint64 externalOperator) private view returns (IMetaRegistry.ExternalOperator memory) {
        return IMetaRegistry.ExternalOperator({ data: abi.encodePacked(bytes1(0), uint8(externalModuleId), externalOperator) });
    }

    function _externalOperatorGroupId(uint64 externalOperator) private view returns (uint256) {
        return metaRegistry.getExternalOperatorGroupId(_ext(externalOperator));
    }
}
