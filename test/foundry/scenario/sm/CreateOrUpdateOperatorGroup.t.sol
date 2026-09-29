// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IBaseModule, IMetaRegistry, INodeOperatorsRegistry, IStakingRouter, NodeOperatorManagementProperties} from "test/foundry/interfaces/External.sol";
import {ICreateOrUpdateOperatorGroup} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `CreateOrUpdateOperatorGroup:CM` of `deployed-sm-<chain>.json`: a motion
///         creates a MetaRegistry operator group, updates one or empties one
contract CreateOrUpdateOperatorGroupTest is EasyTrackScenarioBase {
    string internal constant NEW_GROUP_NAME = "scenario-group";
    string internal constant INITIAL_GROUP_NAME = "initial-group";
    string internal constant UPDATED_GROUP_NAME = "updated-group";
    string internal constant CHANGED_GROUP_NAME = "changed-name";

    IMetaRegistry internal metaRegistry;
    IBaseModule internal module;
    INodeOperatorsRegistry internal externalModule;
    uint256 internal externalModuleId;

    function setUp() public {
        _forkAndInitialize();

        ICreateOrUpdateOperatorGroup factory = ICreateOrUpdateOperatorGroup(
            _factoryAddress(config.smArtifact, "CreateOrUpdateOperatorGroup:CM")
        );
        IStakingRouter stakingRouter = IStakingRouter(factory.stakingRouter());
        metaRegistry = IMetaRegistry(factory.metaRegistry());
        module = IBaseModule(factory.module());
        externalModuleId = factory.allowedExternalModuleId();
        externalModule = INodeOperatorsRegistry(
            stakingRouter.getStakingModule(externalModuleId).stakingModuleAddress
        );

        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
    }

    function testFork_CreatesOperatorGroup() external {
        (uint64 subOperatorId, uint64 externalOperatorId) = _givenGroupMembers();
        uint256 groupsBefore = metaRegistry.getOperatorGroupsCount();
        IMetaRegistry.OperatorGroup memory noGroup;

        _enact(
            abi.encode(
                metaRegistry.NO_GROUP_ID(),
                noGroup,
                _group(
                    NEW_GROUP_NAME,
                    subOperatorId,
                    _externalOperators(externalModuleId, externalOperatorId)
                )
            )
        );

        uint256 groupId = metaRegistry.getOperatorGroupsCount();
        assertEq(groupId, groupsBefore + 1, "getOperatorGroupsCount");
        assertEq(
            metaRegistry.getNodeOperatorGroupId(subOperatorId),
            groupId,
            "getNodeOperatorGroupId"
        );
        assertEq(
            _externalOperatorGroupId(externalOperatorId),
            groupId,
            "getExternalOperatorGroupId"
        );
    }

    function testFork_UpdatesOperatorGroupToNonEmpty() external {
        (
            uint256 groupId,
            uint64 subOperatorId,
            uint64 externalOperatorId
        ) = _givenGroupWithSubOperator();
        IMetaRegistry.OperatorGroup memory current = metaRegistry.getOperatorGroup(groupId);
        IMetaRegistry.OperatorGroup memory updated = _group(
            UPDATED_GROUP_NAME,
            subOperatorId,
            _externalOperators(externalModuleId, externalOperatorId)
        );

        _enact(abi.encode(groupId, current, updated));

        assertEq(
            metaRegistry.getOperatorGroup(groupId).externalOperators.length,
            1,
            "externalOperators.length"
        );
        assertEq(
            _externalOperatorGroupId(externalOperatorId),
            groupId,
            "getExternalOperatorGroupId"
        );
        assertEq(
            metaRegistry.getNodeOperatorGroupId(subOperatorId),
            groupId,
            "getNodeOperatorGroupId"
        );
    }

    function testFork_UpdatesOperatorGroupToEmpty() external {
        (
            uint256 groupId,
            uint64 subOperatorId,
            uint64 externalOperatorId
        ) = _givenGroupWithBothOperators();
        IMetaRegistry.OperatorGroup memory current = metaRegistry.getOperatorGroup(groupId);
        IMetaRegistry.OperatorGroup memory emptyGroup;

        _enact(abi.encode(groupId, current, emptyGroup));

        assertEq(
            metaRegistry.getNodeOperatorGroupId(subOperatorId),
            metaRegistry.NO_GROUP_ID(),
            "getNodeOperatorGroupId"
        );
        assertEq(
            _externalOperatorGroupId(externalOperatorId),
            metaRegistry.NO_GROUP_ID(),
            "getExternalOperatorGroupId"
        );
    }

    function testFork_UpdatesEmptyGroupToEmpty() external {
        (uint256 groupId, uint64 subOperatorId, ) = _givenGroupWithBothOperators();
        IMetaRegistry.OperatorGroup memory emptyGroup;
        metaRegistry.createOrUpdateOperatorGroup(groupId, emptyGroup);
        IMetaRegistry.OperatorGroup memory current = metaRegistry.getOperatorGroup(groupId);

        // An empty -> empty update is a no-op the factory must still validate and Easy Track enact
        _enact(abi.encode(groupId, current, emptyGroup));

        assertEq(
            metaRegistry.getNodeOperatorGroupId(subOperatorId),
            metaRegistry.NO_GROUP_ID(),
            "getNodeOperatorGroupId"
        );
    }

    function testFork_RevertWhen_CurrentGroupChangesBeforeEnact() external {
        (
            uint256 groupId,
            uint64 subOperatorId,
            uint64 externalOperatorId
        ) = _givenGroupWithSubOperator();
        IMetaRegistry.OperatorGroup memory current = metaRegistry.getOperatorGroup(groupId);
        bytes memory callData = abi.encode(
            groupId,
            current,
            _group(
                UPDATED_GROUP_NAME,
                subOperatorId,
                _externalOperators(externalModuleId, externalOperatorId)
            )
        );
        uint256 motionId = _createMotion(callData);

        // Rename the group so the committed current definition no longer matches
        metaRegistry.createOrUpdateOperatorGroup(
            groupId,
            _group(CHANGED_GROUP_NAME, subOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );

        _givenMotionDurationPassed();

        vm.prank(stranger);
        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        easyTrack.enactMotion(motionId, callData);
    }

    /// @dev A fresh curated sub operator and a fresh legacy NOR external operator
    function _givenGroupMembers()
        private
        returns (uint64 subOperatorId, uint64 externalOperatorId)
    {
        _givenRole(address(module), CREATE_NODE_OPERATOR_ROLE, address(this));
        address subOperator = makeAddr("subOperator");
        subOperatorId = uint64(
            module.createNodeOperator(
                subOperator,
                NodeOperatorManagementProperties(subOperator, subOperator, false),
                address(0)
            )
        );

        vm.prank(config.agent);
        externalOperatorId = uint64(
            externalModule.addNodeOperator("scenario-external", makeAddr("externalOperatorReward"))
        );
    }

    /// @dev A group of fresh members holding only the sub operator
    function _givenGroupWithSubOperator()
        private
        returns (
            uint256 groupId,
            uint64 subOperatorId,
            uint64 externalOperatorId
        )
    {
        (subOperatorId, externalOperatorId) = _givenGroupMembers();
        groupId = _givenGroup(subOperatorId, new IMetaRegistry.ExternalOperator[](0));

        assertEq(
            _externalOperatorGroupId(externalOperatorId),
            metaRegistry.NO_GROUP_ID(),
            "setup: getExternalOperatorGroupId"
        );
    }

    /// @dev A group of fresh members holding the sub operator and the external operator
    function _givenGroupWithBothOperators()
        private
        returns (
            uint256 groupId,
            uint64 subOperatorId,
            uint64 externalOperatorId
        )
    {
        (subOperatorId, externalOperatorId) = _givenGroupMembers();
        groupId = _givenGroup(
            subOperatorId,
            _externalOperators(externalModuleId, externalOperatorId)
        );

        assertEq(
            _externalOperatorGroupId(externalOperatorId),
            groupId,
            "setup: getExternalOperatorGroupId"
        );
    }

    /// @dev Create the group directly on the MetaRegistry, the data a motion then updates
    function _givenGroup(
        uint64 subOperatorId,
        IMetaRegistry.ExternalOperator[] memory externalOperators
    ) private returns (uint256 groupId) {
        _givenRole(address(metaRegistry), MANAGE_OPERATOR_GROUPS_ROLE, address(this));
        metaRegistry.createOrUpdateOperatorGroup(
            metaRegistry.NO_GROUP_ID(),
            _group(INITIAL_GROUP_NAME, subOperatorId, externalOperators)
        );
        groupId = metaRegistry.getNodeOperatorGroupId(subOperatorId);

        assertNotEq(groupId, metaRegistry.NO_GROUP_ID(), "setup: getNodeOperatorGroupId");
    }

    function _group(
        string memory name,
        uint64 subOperatorId,
        IMetaRegistry.ExternalOperator[] memory externalOperators
    ) private pure returns (IMetaRegistry.OperatorGroup memory) {
        return
            IMetaRegistry.OperatorGroup({
                name: name,
                subNodeOperators: _subNodeOperators(subOperatorId),
                externalOperators: externalOperators
            });
    }

    function _externalOperatorGroupId(uint64 externalOperatorId) private view returns (uint256) {
        return
            metaRegistry.getExternalOperatorGroupId(
                _externalOperator(externalModuleId, externalOperatorId)
            );
    }
}
