// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AllowConsolidationPair} from "contracts/EVMScriptFactories/AllowConsolidationPair.sol";
import {IConsolidationMigrator} from "contracts/interfaces/IConsolidationMigrator.sol";
import {ConsolidationMigratorStub} from "contracts/test/ConsolidationMigratorStub.sol";
import {CSModuleNodeOperatorsStub} from "contracts/test/CSModuleNodeOperatorsStub.sol";
import {MetaRegistryStub} from "contracts/test/MetaRegistryStub.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {StakingRouterStub} from "contracts/test/StakingRouterStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract AllowConsolidationPairTest is Test {
    uint256 internal constant SOURCE_MODULE_ID = 1;
    uint256 internal constant TARGET_MODULE_ID = 2;
    uint256 internal constant SOURCE_OPERATOR_ID = 0;
    /// @dev python: TARGET_OPERATOR_IDS = [3, 4]
    uint256 internal constant FIRST_TARGET_OPERATOR_ID = 3;
    uint256 internal constant SECOND_TARGET_OPERATOR_ID = 4;
    uint256 internal constant LINKED_GROUP_ID = 1;
    /// @dev python: SOURCE_OPERATOR_ID + 1
    uint256 internal constant SOURCE_NODE_OPERATORS_COUNT = SOURCE_OPERATOR_ID + 1;
    /// @dev python: TARGET_OPERATOR_IDS[-1] + 2
    uint256 internal constant TARGET_NODE_OPERATORS_COUNT = SECOND_TARGET_OPERATOR_ID + 2;
    /// @dev keccak256("MANAGE_SIGNING_KEYS")
    bytes32 internal constant MANAGE_SIGNING_KEYS_ROLE =
        0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee;
    /// @dev ExternalOperatorLib.OperatorType.NOR, the first byte of an external operator key
    bytes1 internal constant EXT_OPERATOR_TYPE_NOR = 0x00;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    CSModuleNodeOperatorsStub internal targetModuleStub;
    NodeOperatorsRegistryStub internal sourceModuleStub;
    MetaRegistryStub internal metaRegistryStub;
    StakingRouterStub internal stakingRouterStub;
    ConsolidationMigratorStub internal consolidationMigratorStub;
    AllowConsolidationPair internal allowConsolidationPair;

    function setUp() public {
        targetModuleStub = new CSModuleNodeOperatorsStub();
        targetModuleStub.setNodeOperatorsCount(TARGET_NODE_OPERATORS_COUNT);
        targetModuleStub.setNodeOperatorIsActive(FIRST_TARGET_OPERATOR_ID, true);
        targetModuleStub.setNodeOperatorIsActive(SECOND_TARGET_OPERATOR_ID, true);

        sourceModuleStub = new NodeOperatorsRegistryStub(owner);
        sourceModuleStub.setDesiredNodeOperatorCount(SOURCE_NODE_OPERATORS_COUNT);
        sourceModuleStub.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, owner);

        metaRegistryStub = new MetaRegistryStub();
        metaRegistryStub.setExternalOperatorGroupId(
            _norData(SOURCE_MODULE_ID, SOURCE_OPERATOR_ID), LINKED_GROUP_ID
        );
        metaRegistryStub.setNodeOperatorGroupId(FIRST_TARGET_OPERATOR_ID, LINKED_GROUP_ID);
        metaRegistryStub.setNodeOperatorGroupId(SECOND_TARGET_OPERATOR_ID, LINKED_GROUP_ID);

        stakingRouterStub = new StakingRouterStub();
        stakingRouterStub.setStakingModule(SOURCE_MODULE_ID, address(sourceModuleStub));
        stakingRouterStub.setStakingModule(TARGET_MODULE_ID, address(targetModuleStub));

        consolidationMigratorStub = new ConsolidationMigratorStub(
            SOURCE_MODULE_ID, TARGET_MODULE_ID, address(stakingRouterStub)
        );
        targetModuleStub.setMetaRegistry(address(metaRegistryStub));

        vm.prank(owner);
        allowConsolidationPair = new AllowConsolidationPair(address(consolidationMigratorStub));

        vm.label(address(targetModuleStub), "targetModuleStub");
        vm.label(address(sourceModuleStub), "sourceModuleStub");
        vm.label(address(metaRegistryStub), "metaRegistryStub");
        vm.label(address(stakingRouterStub), "stakingRouterStub");
        vm.label(address(consolidationMigratorStub), "consolidationMigratorStub");
        vm.label(address(allowConsolidationPair), "allowConsolidationPair");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(
            address(allowConsolidationPair.consolidationMigrator()),
            address(consolidationMigratorStub),
            "consolidationMigrator"
        );
        assertEq(
            address(allowConsolidationPair.stakingRouter()),
            address(stakingRouterStub),
            "stakingRouter"
        );
        assertEq(allowConsolidationPair.sourceModuleId(), SOURCE_MODULE_ID, "sourceModuleId");
        assertEq(allowConsolidationPair.targetModuleId(), TARGET_MODULE_ID, "targetModuleId");
    }

    // python: test_deploy_reverts_with_zero_migrator
    function test_RevertWhen_MigratorIsZero() external {
        vm.expectRevert("ZERO_MIGRATOR");
        new AllowConsolidationPair(address(0));
    }

    // python: test_submitter_must_not_be_zero
    function test_RevertWhen_SubmitterIsZero() external {
        vm.expectRevert("ZERO_SUBMITTER");
        allowConsolidationPair.createEVMScript(owner, _callData(address(0)));
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.prank(stranger);
        vm.expectRevert("CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER");
        allowConsolidationPair.createEVMScript(stranger, _callData(stranger));
    }

    // python: test_source_operator_must_exist
    function test_RevertWhen_SourceOperatorDoesNotExist() external {
        vm.expectRevert("SOURCE_OPERATOR_ID_DOES_NOT_EXIST");
        allowConsolidationPair.createEVMScript(owner, _callData(owner, SOURCE_OPERATOR_ID + 1));
    }

    // python: test_source_operator_out_of_range
    function test_RevertWhen_SourceOperatorIsOutOfRange() external {
        sourceModuleStub.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID);

        vm.expectRevert("SOURCE_OPERATOR_ID_DOES_NOT_EXIST");
        allowConsolidationPair.createEVMScript(owner, _callData(owner));
    }

    // python: test_source_operator_must_be_active
    function test_RevertWhen_SourceOperatorIsNotActive() external {
        sourceModuleStub.setActive(SOURCE_OPERATOR_ID, false);

        vm.expectRevert("NODE_OPERATOR_IS_NOT_ACTIVE");
        allowConsolidationPair.createEVMScript(owner, _callData(owner));
    }

    // python: test_caller_must_match_owner
    function test_RevertWhen_CreatorIsNotSourceOperatorOwner() external {
        sourceModuleStub.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, stranger);

        vm.expectRevert("CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER");
        allowConsolidationPair.createEVMScript(owner, _callData(owner));
    }

    // python: test_caller_with_manage_signing_keys_role_can_create_script
    function test_CreatesEVMScriptForManageSigningKeysRoleHolder() external {
        sourceModuleStub.setCanPerform(stranger, MANAGE_SIGNING_KEYS_ROLE, SOURCE_OPERATOR_ID, true);

        bytes memory evmScript = allowConsolidationPair.createEVMScript(stranger, _callData(owner));

        assertEq(
            evmScript,
            _allowPairsScript(
                owner, _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, SECOND_TARGET_OPERATOR_ID)
            ),
            "evmScript"
        );
    }

    // python: test_validation_uses_creator_not_tx_sender
    function test_ValidatesCreatorNotSender() external {
        vm.prank(stranger);
        bytes memory evmScript = allowConsolidationPair.createEVMScript(owner, _callData(owner));

        assertEq(
            evmScript,
            _allowPairsScript(
                owner, _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, SECOND_TARGET_OPERATOR_ID)
            ),
            "evmScript"
        );
    }

    // python: test_target_operator_ids_must_not_be_empty
    function test_RevertWhen_TargetOperatorIdsAreEmpty() external {
        vm.expectRevert("EMPTY_TARGET_OPERATOR_IDS");
        allowConsolidationPair.createEVMScript(owner, _callData(owner, new uint256[](0)));
    }

    // python: test_target_operator_ids_must_be_sorted_ascending
    function test_RevertWhen_TargetOperatorIdsAreNotSorted() external {
        vm.expectRevert("TARGET_OPERATOR_IDS_NOT_SORTED");
        allowConsolidationPair.createEVMScript(
            owner,
            _callData(
                owner, _targetOperatorIds(SECOND_TARGET_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID)
            )
        );
    }

    // python: test_target_operator_ids_must_not_have_duplicates
    function test_RevertWhen_TargetOperatorIdsHaveDuplicates() external {
        vm.expectRevert("TARGET_OPERATOR_IDS_NOT_SORTED");
        allowConsolidationPair.createEVMScript(
            owner,
            _callData(owner, _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID))
        );
    }

    // python: test_target_operator_must_be_active
    function test_RevertWhen_TargetOperatorIsNotActive() external {
        targetModuleStub.setNodeOperatorIsActive(FIRST_TARGET_OPERATOR_ID, false);

        vm.expectRevert("NODE_OPERATOR_IS_NOT_ACTIVE");
        allowConsolidationPair.createEVMScript(owner, _callData(owner));
    }

    // python: test_source_must_have_group_id_in_meta_registry
    function test_RevertWhen_SourceOperatorHasNoGroup() external {
        metaRegistryStub.setExternalOperatorGroupId(
            _norData(SOURCE_MODULE_ID, SOURCE_OPERATOR_ID), 0
        );

        vm.expectRevert("OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY");
        allowConsolidationPair.createEVMScript(owner, _callData(owner));
    }

    // python: test_source_and_targets_must_be_linked_via_meta_registry
    function test_RevertWhen_SourceAndTargetsAreNotLinked() external {
        metaRegistryStub.setExternalOperatorGroupId(
            _norData(SOURCE_MODULE_ID, SOURCE_OPERATOR_ID), LINKED_GROUP_ID + 1
        );

        vm.expectRevert("OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY");
        allowConsolidationPair.createEVMScript(owner, _callData(owner));
    }

    // python: test_target_operator_must_be_linked_via_meta_registry
    function test_RevertWhen_TargetOperatorIsNotLinked() external {
        metaRegistryStub.setNodeOperatorGroupId(FIRST_TARGET_OPERATOR_ID, LINKED_GROUP_ID + 1);

        vm.expectRevert("OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY");
        allowConsolidationPair.createEVMScript(
            owner, _callData(owner, _targetOperatorIds(FIRST_TARGET_OPERATOR_ID))
        );
    }

    // python: test_create_evm_script_when_pair_is_already_allowed
    function test_CreatesEVMScriptWhenPairIsAlreadyAllowed() external {
        consolidationMigratorStub.setPairStatus(SOURCE_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID, true);

        bytes memory evmScript = allowConsolidationPair.createEVMScript(owner, _callData(owner));

        assertEq(
            evmScript,
            _allowPairsScript(
                owner, _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, SECOND_TARGET_OPERATOR_ID)
            ),
            "evmScript"
        );
    }

    // python: test_consolidation_migrator_stub_overwrites_submitter_without_duplicate_target
    function test_MigratorStubOverwritesSubmitterWithoutDuplicateTarget() external {
        consolidationMigratorStub.allowPair(SOURCE_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID, owner);

        assertEq(
            consolidationMigratorStub.getSubmitter(SOURCE_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID),
            owner,
            "submitter"
        );
        assertEq(
            consolidationMigratorStub.getAllowedTargets(SOURCE_OPERATOR_ID),
            _targetOperatorIds(FIRST_TARGET_OPERATOR_ID),
            "allowedTargets"
        );

        consolidationMigratorStub.allowPair(SOURCE_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID, stranger);

        assertEq(
            consolidationMigratorStub.getSubmitter(SOURCE_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID),
            stranger,
            "submitter after overwrite"
        );
        assertEq(
            consolidationMigratorStub.getAllowedTargets(SOURCE_OPERATOR_ID),
            _targetOperatorIds(FIRST_TARGET_OPERATOR_ID),
            "allowedTargets after overwrite"
        );

        consolidationMigratorStub.disallowPair(SOURCE_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID);

        assertEq(
            consolidationMigratorStub.getSubmitter(SOURCE_OPERATOR_ID, FIRST_TARGET_OPERATOR_ID),
            address(0),
            "submitter after disallow"
        );
        assertEq(
            consolidationMigratorStub.getAllowedTargets(SOURCE_OPERATOR_ID),
            new uint256[](0),
            "allowedTargets after disallow"
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = allowConsolidationPair.createEVMScript(owner, _callData(owner));

        assertEq(
            evmScript,
            _allowPairsScript(
                owner, _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, SECOND_TARGET_OPERATOR_ID)
            ),
            "evmScript"
        );
    }

    // python: test_create_evm_script_with_single_target
    function test_CreatesEVMScriptWithSingleTarget() external view {
        uint256[] memory singleTargetIds = _targetOperatorIds(FIRST_TARGET_OPERATOR_ID);

        bytes memory evmScript =
            allowConsolidationPair.createEVMScript(owner, _callData(owner, singleTargetIds));

        assertEq(evmScript, _allowPairsScript(owner, singleTargetIds), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        AllowConsolidationPair.AllowConsolidationPairInput memory decoded =
            allowConsolidationPair.decodeEVMScriptCallData(_callData(owner));

        assertEq(decoded.submitter, owner, "submitter");
        assertEq(decoded.sourceOperatorId, SOURCE_OPERATOR_ID, "sourceOperatorId");
        assertEq(
            decoded.targetOperatorIds,
            _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, SECOND_TARGET_OPERATOR_ID),
            "targetOperatorIds"
        );
    }

    // python: test_decode_evm_script_call_data_reverts_on_invalid_calldata
    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        allowConsolidationPair.decodeEVMScriptCallData("");
    }

    function _targetOperatorIds(uint256 single) private pure returns (uint256[] memory ids) {
        ids = new uint256[](1);
        ids[0] = single;
    }

    function _targetOperatorIds(uint256 first, uint256 second)
        private
        pure
        returns (uint256[] memory ids)
    {
        ids = new uint256[](2);
        ids[0] = first;
        ids[1] = second;
    }

    /// @dev python: EXT, the ten-byte NOR external operator key
    function _norData(uint256 moduleId, uint256 nodeOperatorId)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(EXT_OPERATOR_TYPE_NOR, uint8(moduleId), uint64(nodeOperatorId));
    }

    /// @dev python: C with the default source operator and target ids
    function _callData(address submitter) private pure returns (bytes memory) {
        return _callData(
            submitter,
            SOURCE_OPERATOR_ID,
            _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, SECOND_TARGET_OPERATOR_ID)
        );
    }

    /// @dev python: C with the default target ids
    function _callData(address submitter, uint256 sourceOperatorId)
        private
        pure
        returns (bytes memory)
    {
        return _callData(
            submitter,
            sourceOperatorId,
            _targetOperatorIds(FIRST_TARGET_OPERATOR_ID, SECOND_TARGET_OPERATOR_ID)
        );
    }

    /// @dev python: C with the default source operator
    function _callData(address submitter, uint256[] memory targetOperatorIds)
        private
        pure
        returns (bytes memory)
    {
        return _callData(submitter, SOURCE_OPERATOR_ID, targetOperatorIds);
    }

    /// @dev python: C
    function _callData(
        address submitter,
        uint256 sourceOperatorId,
        uint256[] memory targetOperatorIds
    ) private pure returns (bytes memory) {
        return abi.encode(submitter, sourceOperatorId, targetOperatorIds);
    }

    /// @dev python: S, encode_call_script of one migrator.allowPair per target id
    function _allowPairsScript(address submitter, uint256[] memory targetOperatorIds)
        private
        view
        returns (bytes memory)
    {
        bytes[] memory calls = new bytes[](targetOperatorIds.length);

        for (uint256 i; i < targetOperatorIds.length; ++i) {
            calls[i] = abi.encodeWithSelector(
                IConsolidationMigrator.allowPair.selector,
                SOURCE_OPERATOR_ID,
                targetOperatorIds[i],
                submitter
            );
        }

        return EVMScripts.encodeCallScript(address(consolidationMigratorStub), calls);
    }
}
