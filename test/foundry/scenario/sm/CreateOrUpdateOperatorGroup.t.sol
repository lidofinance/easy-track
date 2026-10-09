// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {
    IBaseModule,
    IMetaRegistry,
    INodeOperatorsRegistry,
    IStakingRouter,
    NodeOperatorManagementProperties
} from "test/foundry/interfaces/External.sol";
import {ICreateOrUpdateOperatorGroup} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `CreateOrUpdateOperatorGroup:CM` of `deployed-sm-<chain>.json`: a motion
///         creates a MetaRegistry operator group, updates one or empties one
contract CreateOrUpdateOperatorGroupTest is EasyTrackScenarioBase {
    string internal constant NEW_GROUP_NAME = "scenario-group";
    string internal constant INITIAL_GROUP_NAME = "initial-group";
    string internal constant UPDATED_GROUP_NAME = "updated-group";
    string internal constant CHANGED_GROUP_NAME = "changed-name";
    string internal constant GROUP_A_NAME = "group-a";
    string internal constant GROUP_B_NAME = "group-b";

    /// @dev Two sub operators sharing a group equally
    uint16 internal constant HALF_SHARE = FULL_SHARE / 2;

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

    // python: test_create_operator_group_via_motion_scenario
    function testFork_CreatesOperatorGroup() external {
        (uint64 subOperatorId, uint64 externalOperatorId) = _createGroupMembers();
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
            metaRegistry.getNodeOperatorGroupId(subOperatorId), groupId, "getNodeOperatorGroupId"
        );
        assertEq(
            _externalOperatorGroupId(externalOperatorId), groupId, "getExternalOperatorGroupId"
        );
    }

    // python: test_update_operator_group_via_motion_scenario
    function testFork_UpdatesOperatorGroupToNonEmpty() external {
        (uint256 groupId, uint64 subOperatorId, uint64 externalOperatorId) =
            _createGroupWithSubOperator();
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
            _externalOperatorGroupId(externalOperatorId), groupId, "getExternalOperatorGroupId"
        );
        assertEq(
            metaRegistry.getNodeOperatorGroupId(subOperatorId), groupId, "getNodeOperatorGroupId"
        );
    }

    // python: test_clear_operator_group_via_motion_scenario
    function testFork_UpdatesOperatorGroupToEmpty() external {
        (uint256 groupId, uint64 subOperatorId, uint64 externalOperatorId) =
            _createGroupWithBothOperators();
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
        (uint256 groupId, uint64 subOperatorId,) = _createGroupWithBothOperators();
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

    // python: test_migrate_sub_operator_between_groups_scenario
    function testFork_MigratesSubOperatorToNewGroup() external {
        (uint64 stayingOperatorId, uint64 migratingOperatorId) = _createSubOperatorPair();
        uint256 groupsBefore = metaRegistry.getOperatorGroupsCount();
        uint256 groupAId = _createGroup(
            _group(
                GROUP_A_NAME,
                _splitSubNodeOperators(stayingOperatorId, migratingOperatorId),
                new IMetaRegistry.ExternalOperator[](0)
            )
        );
        IMetaRegistry.OperatorGroup memory noGroup;
        bytes memory releaseCallData = abi.encode(
            groupAId,
            metaRegistry.getOperatorGroup(groupAId),
            _group(GROUP_A_NAME, stayingOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );
        bytes memory claimCallData = abi.encode(
            metaRegistry.NO_GROUP_ID(),
            noGroup,
            _group(GROUP_B_NAME, migratingOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );

        // Both motions are pending at once: the factory is stateless, so the overlap is caught
        // only at enactment, in order
        uint256 releaseMotionId = _createMotion(releaseCallData);
        uint256 claimMotionId = _createMotion(claimCallData);

        _passMotionDuration();

        vm.prank(stranger);
        easyTrack.enactMotion(releaseMotionId, releaseCallData);

        vm.prank(stranger);
        easyTrack.enactMotion(claimMotionId, claimCallData);

        assertEq(metaRegistry.getOperatorGroupsCount(), groupsBefore + 2, "getOperatorGroupsCount");
        assertEq(
            metaRegistry.getNodeOperatorGroupId(stayingOperatorId),
            groupAId,
            "staying getNodeOperatorGroupId"
        );
        assertEq(
            metaRegistry.getNodeOperatorGroupId(migratingOperatorId),
            groupsBefore + 2,
            "migrating getNodeOperatorGroupId"
        );
    }

    // python: test_migrate_sub_operator_between_existing_groups_scenario
    function testFork_MigratesSubOperatorBetweenExistingGroups() external {
        (uint64 stayingOperatorId, uint64 migratingOperatorId) = _createSubOperatorPair();
        uint64 receivingOperatorId = _createSubOperator("receivingSubOperator");
        uint256 groupsBefore = metaRegistry.getOperatorGroupsCount();
        uint256 groupAId = _createGroup(
            _group(
                GROUP_A_NAME,
                _splitSubNodeOperators(stayingOperatorId, migratingOperatorId),
                new IMetaRegistry.ExternalOperator[](0)
            )
        );
        uint256 groupBId = _createGroup(
            _group(GROUP_B_NAME, receivingOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );
        bytes memory releaseCallData = abi.encode(
            groupAId,
            metaRegistry.getOperatorGroup(groupAId),
            _group(GROUP_A_NAME, stayingOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );
        bytes memory claimCallData = abi.encode(
            groupBId,
            metaRegistry.getOperatorGroup(groupBId),
            _group(
                GROUP_B_NAME,
                _splitSubNodeOperators(migratingOperatorId, receivingOperatorId),
                new IMetaRegistry.ExternalOperator[](0)
            )
        );
        uint256 releaseMotionId = _createMotion(releaseCallData);
        uint256 claimMotionId = _createMotion(claimCallData);

        _passMotionDuration();

        vm.prank(stranger);
        easyTrack.enactMotion(releaseMotionId, releaseCallData);

        vm.prank(stranger);
        easyTrack.enactMotion(claimMotionId, claimCallData);

        assertEq(metaRegistry.getOperatorGroupsCount(), groupsBefore + 2, "getOperatorGroupsCount");
        assertEq(
            metaRegistry.getNodeOperatorGroupId(stayingOperatorId),
            groupAId,
            "staying getNodeOperatorGroupId"
        );
        assertEq(
            metaRegistry.getNodeOperatorGroupId(migratingOperatorId),
            groupBId,
            "migrating getNodeOperatorGroupId"
        );
        assertEq(
            metaRegistry.getNodeOperatorGroupId(receivingOperatorId),
            groupBId,
            "receiving getNodeOperatorGroupId"
        );
    }

    // python: test_migrate_sub_operator_conflict_scenario
    function testFork_RevertWhen_NewGroupClaimsOperatorOfAnotherGroup() external {
        (uint64 stayingOperatorId, uint64 migratingOperatorId) = _createSubOperatorPair();
        uint256 groupsBefore = metaRegistry.getOperatorGroupsCount();
        IMetaRegistry.OperatorGroup memory noGroup;
        _enact(
            abi.encode(
                metaRegistry.NO_GROUP_ID(),
                noGroup,
                _group(
                    GROUP_A_NAME,
                    _splitSubNodeOperators(stayingOperatorId, migratingOperatorId),
                    new IMetaRegistry.ExternalOperator[](0)
                )
            )
        );
        uint256 groupAId = groupsBefore + 1;
        bytes memory releaseCallData = abi.encode(
            groupAId,
            metaRegistry.getOperatorGroup(groupAId),
            _group(GROUP_A_NAME, stayingOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );
        bytes memory claimCallData = abi.encode(
            metaRegistry.NO_GROUP_ID(),
            noGroup,
            _group(GROUP_B_NAME, migratingOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );
        _createMotion(releaseCallData);
        uint256 claimMotionId = _createMotion(claimCallData);

        _passMotionDuration();

        // Enacted before the release, the claim meets an operator still in group A. The
        // MetaRegistry source is outside this repository, so its error is not pinned.
        vm.prank(stranger);
        vm.expectRevert();
        easyTrack.enactMotion(claimMotionId, claimCallData);

        assertEq(metaRegistry.getOperatorGroupsCount(), groupsBefore + 1, "getOperatorGroupsCount");
    }

    function testFork_RevertWhen_CurrentGroupChangesBeforeEnact() external {
        (uint256 groupId, uint64 subOperatorId, uint64 externalOperatorId) =
            _createGroupWithSubOperator();
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

        _passMotionDuration();

        vm.prank(stranger);
        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        easyTrack.enactMotion(motionId, callData);
    }

    /// @dev A fresh curated sub operator and a fresh legacy NOR external operator
    function _createGroupMembers()
        private
        returns (uint64 subOperatorId, uint64 externalOperatorId)
    {
        subOperatorId = _createSubOperator("subOperator");

        vm.prank(config.agent);
        externalOperatorId = uint64(
            externalModule.addNodeOperator("scenario-external", makeAddr("externalOperatorReward"))
        );
    }

    /// @dev Two fresh curated sub operators in id order, one to keep in its group and one to move
    ///      out of it
    function _createSubOperatorPair()
        private
        returns (uint64 stayingOperatorId, uint64 migratingOperatorId)
    {
        stayingOperatorId = _createSubOperator("stayingSubOperator");
        migratingOperatorId = _createSubOperator("migratingSubOperator");
    }

    /// @dev A fresh curated operator of the module
    function _createSubOperator(string memory label) private returns (uint64) {
        _grantRole(address(module), CREATE_NODE_OPERATOR_ROLE, address(this));
        address subOperator = makeAddr(label);

        return uint64(
            module.createNodeOperator(
                subOperator,
                NodeOperatorManagementProperties(subOperator, subOperator, false),
                address(0)
            )
        );
    }

    /// @dev A group of fresh members holding only the sub operator
    function _createGroupWithSubOperator()
        private
        returns (uint256 groupId, uint64 subOperatorId, uint64 externalOperatorId)
    {
        (subOperatorId, externalOperatorId) = _createGroupMembers();
        groupId = _createGroup(
            _group(INITIAL_GROUP_NAME, subOperatorId, new IMetaRegistry.ExternalOperator[](0))
        );

        assertEq(
            _externalOperatorGroupId(externalOperatorId),
            metaRegistry.NO_GROUP_ID(),
            "setup: getExternalOperatorGroupId"
        );
    }

    /// @dev A group of fresh members holding the sub operator and the external operator
    function _createGroupWithBothOperators()
        private
        returns (uint256 groupId, uint64 subOperatorId, uint64 externalOperatorId)
    {
        (subOperatorId, externalOperatorId) = _createGroupMembers();
        groupId = _createGroup(
            _group(
                INITIAL_GROUP_NAME,
                subOperatorId,
                _externalOperators(externalModuleId, externalOperatorId)
            )
        );

        assertEq(
            _externalOperatorGroupId(externalOperatorId),
            groupId,
            "setup: getExternalOperatorGroupId"
        );
    }

    /// @dev Create the group directly on the MetaRegistry, the data a motion then updates
    function _createGroup(IMetaRegistry.OperatorGroup memory group)
        private
        returns (uint256 groupId)
    {
        _grantRole(address(metaRegistry), MANAGE_OPERATOR_GROUPS_ROLE, address(this));
        metaRegistry.createOrUpdateOperatorGroup(metaRegistry.NO_GROUP_ID(), group);
        groupId = metaRegistry.getNodeOperatorGroupId(group.subNodeOperators[0].nodeOperatorId);

        assertNotEq(groupId, metaRegistry.NO_GROUP_ID(), "setup: getNodeOperatorGroupId");
    }

    function _group(
        string memory name,
        uint64 subOperatorId,
        IMetaRegistry.ExternalOperator[] memory externalOperators
    ) private pure returns (IMetaRegistry.OperatorGroup memory) {
        return _group(name, _subNodeOperators(subOperatorId), externalOperators);
    }

    function _group(
        string memory name,
        IMetaRegistry.SubNodeOperator[] memory subNodeOperators,
        IMetaRegistry.ExternalOperator[] memory externalOperators
    ) private pure returns (IMetaRegistry.OperatorGroup memory) {
        return IMetaRegistry.OperatorGroup({
            name: name, subNodeOperators: subNodeOperators, externalOperators: externalOperators
        });
    }

    /// @dev Two sub operators sharing a group equally, in the id order the factory requires
    function _splitSubNodeOperators(uint64 firstOperatorId, uint64 secondOperatorId)
        private
        pure
        returns (IMetaRegistry.SubNodeOperator[] memory subNodeOperators)
    {
        subNodeOperators = new IMetaRegistry.SubNodeOperator[](2);
        subNodeOperators[0] =
            IMetaRegistry.SubNodeOperator({nodeOperatorId: firstOperatorId, share: HALF_SHARE});
        subNodeOperators[1] =
            IMetaRegistry.SubNodeOperator({nodeOperatorId: secondOperatorId, share: HALF_SHARE});
    }

    function _externalOperatorGroupId(uint64 externalOperatorId) private view returns (uint256) {
        return metaRegistry.getExternalOperatorGroupId(
            _externalOperator(externalModuleId, externalOperatorId)
        );
    }
}
