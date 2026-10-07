// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    CreateOrUpdateOperatorGroup,
    ICreateOrUpdateOperatorGroup
} from "contracts/EVMScriptFactories/CreateOrUpdateOperatorGroup.sol";
import {IMetaRegistry} from "contracts/interfaces/IMetaRegistry.sol";
import {CuratedModuleStub} from "contracts/test/CuratedModuleStub.sol";
import {MetaRegistryStub} from "contracts/test/MetaRegistryStub.sol";
import {StakingRouterStub} from "contracts/test/StakingRouterStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract CreateOrUpdateOperatorGroupTest is Test {
    string internal constant FACTORY_NAME = "CM v2";
    uint256 internal constant ALLOWED_EXTERNAL_MODULE_ID = 1;
    uint256 internal constant ANOTHER_EXTERNAL_MODULE_ID = 2;
    uint256 internal constant UNREGISTERED_EXTERNAL_MODULE_ID = 99;
    uint256 internal constant MODULE_NODE_OPERATORS_COUNT = 100;
    uint256 internal constant EXTERNAL_MODULE_NODE_OPERATORS_COUNT = 10_000;
    /// @dev python: group_id = 0, the stub's default NO_GROUP_ID, selects the create path
    uint256 internal constant NO_GROUP_ID = 0;
    uint256 internal constant NON_ZERO_NO_GROUP_ID = 10;
    uint16 internal constant MAX_BP = 10_000;
    uint256 internal constant MAX_NAME_LENGTH = 256;
    /// @dev ExternalOperatorLib.OperatorType.NOR, the first byte of an external operator key
    bytes1 internal constant EXT_OPERATOR_TYPE_NOR = 0x00;
    bytes1 internal constant UNSUPPORTED_EXT_OPERATOR_TYPE = 0x01;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    CuratedModuleStub internal curatedModuleStub;
    MetaRegistryStub internal metaRegistryStub;
    StakingRouterStub internal stakingRouterStub;
    CreateOrUpdateOperatorGroup internal createOrUpdateOperatorGroup;

    function setUp() public {
        curatedModuleStub = new CuratedModuleStub();
        curatedModuleStub.mock_setNodeOperatorsCount(MODULE_NODE_OPERATORS_COUNT);

        CuratedModuleStub firstExternalModule = new CuratedModuleStub();
        firstExternalModule.mock_setNodeOperatorsCount(EXTERNAL_MODULE_NODE_OPERATORS_COUNT);
        CuratedModuleStub secondExternalModule = new CuratedModuleStub();
        secondExternalModule.mock_setNodeOperatorsCount(EXTERNAL_MODULE_NODE_OPERATORS_COUNT);

        stakingRouterStub = new StakingRouterStub();
        stakingRouterStub.setStakingModule(ALLOWED_EXTERNAL_MODULE_ID, address(firstExternalModule));
        stakingRouterStub.setStakingModule(
            ANOTHER_EXTERNAL_MODULE_ID, address(secondExternalModule)
        );

        metaRegistryStub = new MetaRegistryStub();
        metaRegistryStub.setModule(address(curatedModuleStub));
        metaRegistryStub.setStakingRouter(address(stakingRouterStub));
        curatedModuleStub.mock_setMetaRegistry(address(metaRegistryStub));

        vm.prank(owner);
        createOrUpdateOperatorGroup = new CreateOrUpdateOperatorGroup(
            owner, FACTORY_NAME, address(curatedModuleStub), ALLOWED_EXTERNAL_MODULE_ID
        );

        vm.label(address(curatedModuleStub), "curatedModuleStub");
        vm.label(address(firstExternalModule), "firstExternalModule");
        vm.label(address(secondExternalModule), "secondExternalModule");
        vm.label(address(stakingRouterStub), "stakingRouterStub");
        vm.label(address(metaRegistryStub), "metaRegistryStub");
        vm.label(address(createOrUpdateOperatorGroup), "createOrUpdateOperatorGroup");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(createOrUpdateOperatorGroup.trustedCaller(), owner, "trustedCaller");
        assertEq(createOrUpdateOperatorGroup.name(), FACTORY_NAME, "name");
        assertEq(
            address(createOrUpdateOperatorGroup.module()), address(curatedModuleStub), "module"
        );
        assertEq(
            address(createOrUpdateOperatorGroup.metaRegistry()),
            address(metaRegistryStub),
            "metaRegistry"
        );
        assertEq(
            address(createOrUpdateOperatorGroup.stakingRouter()),
            metaRegistryStub.STAKING_ROUTER(),
            "stakingRouter"
        );
        assertEq(
            createOrUpdateOperatorGroup.allowedExternalModuleId(),
            ALLOWED_EXTERNAL_MODULE_ID,
            "allowedExternalModuleId"
        );
    }

    // python: test_deploy_reverts_with_zero_module
    function test_RevertWhen_ModuleIsZero() external {
        vm.expectRevert("ZERO_MODULE_ADDRESS");
        new CreateOrUpdateOperatorGroup(owner, FACTORY_NAME, address(0), 0);
    }

    // python: test_deploy_reverts_with_zero_trusted_caller
    function test_RevertWhen_TrustedCallerIsZero() external {
        vm.expectRevert("TRUSTED_CALLER_IS_ZERO_ADDRESS");
        new CreateOrUpdateOperatorGroup(address(0), FACTORY_NAME, address(curatedModuleStub), 0);
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        createOrUpdateOperatorGroup.createEVMScript(stranger, "");
    }

    // python: test_encode_nor_external_operator_data
    function test_EncodesNORExtOperatorData() external view {
        bytes memory encoded = createOrUpdateOperatorGroup.encodeNORExtOperatorData(7, 255);

        assertEq(encoded, hex"000700000000000000ff", "encoded");
    }

    // python: test_decode_nor_external_operator_data
    function test_DecodesNORExtOperatorData() external view {
        (uint8 moduleId, uint64 nodeOperatorId) =
            createOrUpdateOperatorGroup.decodeNORExtOperatorData(hex"000700000000000000ff");

        assertEq(moduleId, 7, "moduleId");
        assertEq(nodeOperatorId, 255, "nodeOperatorId");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        IMetaRegistry.OperatorGroup memory groupInfo = _group(
            "some_name",
            _subNodeOperators(1, 6000, 2, 4000),
            _externalOperators(
                _norData(ALLOWED_EXTERNAL_MODULE_ID, 11), _norData(ANOTHER_EXTERNAL_MODULE_ID, 22)
            )
        );

        (
            uint256 decodedGroupId,
            IMetaRegistry.OperatorGroup memory decodedCurrentGroupInfo,
            IMetaRegistry.OperatorGroup memory decodedGroupInfo
        ) = createOrUpdateOperatorGroup.decodeEVMScriptCallData(_callData(NO_GROUP_ID, groupInfo));

        assertEq(decodedGroupId, NO_GROUP_ID, "groupId");
        _assertOperatorGroupEq(decodedCurrentGroupInfo, _emptyGroup(), "currentGroupInfo");
        _assertOperatorGroupEq(decodedGroupInfo, groupInfo, "groupInfo");
    }

    // python: test_decode_reverts_with_invalid_calldata[empty]
    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        createOrUpdateOperatorGroup.decodeEVMScriptCallData("");
    }

    // python: test_decode_reverts_with_invalid_calldata[malformed]
    function test_RevertWhen_DecodingMalformedCallData() external {
        vm.expectRevert(bytes(""));
        createOrUpdateOperatorGroup.decodeEVMScriptCallData(hex"01");
    }

    // python: test_create_evm_script_reverts_with_malformed_calldata
    function test_RevertWhen_CreateEVMScriptCallDataIsMalformed() external {
        vm.expectRevert(bytes(""));
        createOrUpdateOperatorGroup.createEVMScript(owner, hex"01");
    }

    // python: test_create_group_success
    function test_CreatesGroup() external view {
        IMetaRegistry.OperatorGroup memory groupInfo = _group(
            "Test Group",
            _subNodeOperators(1, 7000, 2, 3000),
            _externalOperators(
                _norData(ALLOWED_EXTERNAL_MODULE_ID, 1001),
                _norData(ALLOWED_EXTERNAL_MODULE_ID, 2002)
            )
        );

        bytes memory evmScript =
            createOrUpdateOperatorGroup.createEVMScript(owner, _callData(NO_GROUP_ID, groupInfo));

        assertEq(evmScript, _createOrUpdateGroupScript(NO_GROUP_ID, groupInfo), "evmScript");
    }

    // python: test_create_group_reverts_with_empty_sub_node_operators
    function test_RevertWhen_CreatingGroupWithEmptySubNodeOperators() external {
        vm.expectRevert("EMPTY_GROUP");
        createOrUpdateOperatorGroup.createEVMScript(
            owner, _callData(NO_GROUP_ID, _group("", _subNodeOperators(), _externalOperators()))
        );
    }

    // python: test_create_group_reverts_with_empty_sub_node_operators_and_non_empty_external
    function test_RevertWhen_CreatingGroupWithEmptySubNodeOperatorsAndExternalOperators() external {
        vm.expectRevert("EMPTY_GROUP");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    "",
                    _subNodeOperators(),
                    _externalOperators(_norData(ALLOWED_EXTERNAL_MODULE_ID, 1))
                )
            )
        );
    }

    // python: test_create_group_reverts_with_unsorted_sub_node_operators
    function test_RevertWhen_CreatingGroupWithUnsortedSubNodeOperators() external {
        vm.expectRevert("SUB_NODE_OPERATORS_NOT_SORTED");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID, _group("", _subNodeOperators(2, 5000, 1, 5000), _externalOperators())
            )
        );
    }

    // python: test_create_group_reverts_with_duplicate_sub_node_operators
    function test_RevertWhen_CreatingGroupWithDuplicateSubNodeOperators() external {
        vm.expectRevert("SUB_NODE_OPERATORS_NOT_SORTED");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID, _group("", _subNodeOperators(1, 5000, 1, 5000), _externalOperators())
            )
        );
    }

    // python: test_create_group_reverts_with_shares_sum_mismatch
    function test_RevertWhen_CreatingGroupWithSharesSumMismatch() external {
        vm.expectRevert("SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID, _group("", _subNodeOperators(1, 5000, 2, 4000), _externalOperators())
            )
        );
    }

    // python: test_create_group_reverts_with_unsorted_external_operators
    function test_RevertWhen_CreatingGroupWithUnsortedExternalOperators() external {
        vm.expectRevert("EXTERNAL_OPERATORS_NOT_SORTED");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    "",
                    _subNodeOperators(1, MAX_BP),
                    _externalOperators(
                        _norData(ALLOWED_EXTERNAL_MODULE_ID, 2),
                        _norData(ALLOWED_EXTERNAL_MODULE_ID, 1)
                    )
                )
            )
        );
    }

    // python: test_create_group_reverts_with_duplicate_external_operators
    function test_RevertWhen_CreatingGroupWithDuplicateExternalOperators() external {
        vm.expectRevert("EXTERNAL_OPERATORS_NOT_SORTED");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    "",
                    _subNodeOperators(1, MAX_BP),
                    _externalOperators(
                        _norData(ALLOWED_EXTERNAL_MODULE_ID, 1),
                        _norData(ALLOWED_EXTERNAL_MODULE_ID, 1)
                    )
                )
            )
        );
    }

    // python: test_create_group_reverts_with_missing_sub_node_operator
    function test_RevertWhen_CreatingGroupWithMissingSubNodeOperator() external {
        vm.expectRevert("SUB_NODE_OPERATOR_DOES_NOT_EXIST");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    "",
                    _subNodeOperators(uint64(MODULE_NODE_OPERATORS_COUNT), MAX_BP),
                    _externalOperators()
                )
            )
        );
    }

    // python: test_create_group_reverts_with_invalid_external_operator_data_length
    function test_RevertWhen_CreatingGroupWithInvalidExternalOperatorDataLength() external {
        vm.expectRevert("INVALID_EXTERNAL_OPERATOR_DATA_LENGTH");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID, _group("", _subNodeOperators(1, MAX_BP), _externalOperators(hex"0001"))
            )
        );
    }

    // python: test_create_group_reverts_with_unsupported_external_operator_type
    function test_RevertWhen_CreatingGroupWithUnsupportedExternalOperatorType() external {
        bytes memory unsupportedData =
            abi.encodePacked(UNSUPPORTED_EXT_OPERATOR_TYPE, uint8(1), uint64(1));

        vm.expectRevert("UNSUPPORTED_EXTERNAL_OPERATOR_TYPE");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group("", _subNodeOperators(1, MAX_BP), _externalOperators(unsupportedData))
            )
        );
    }

    // python: test_create_group_reverts_with_not_allowed_external_module
    function test_RevertWhen_CreatingGroupWithNotAllowedExternalModule() external {
        vm.expectRevert("EXTERNAL_MODULE_NOT_ALLOWED");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    "",
                    _subNodeOperators(1, MAX_BP),
                    _externalOperators(_norData(ANOTHER_EXTERNAL_MODULE_ID, 1))
                )
            )
        );
    }

    // python: test_create_group_reverts_with_missing_external_module
    function test_RevertWhen_CreatingGroupWithMissingExternalModule() external {
        vm.expectRevert("EXTERNAL_MODULE_NOT_ALLOWED");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    "",
                    _subNodeOperators(1, MAX_BP),
                    _externalOperators(_norData(UNREGISTERED_EXTERNAL_MODULE_ID, 1))
                )
            )
        );
    }

    // python: test_create_group_reverts_with_missing_external_operator
    function test_RevertWhen_CreatingGroupWithMissingExternalOperator() external {
        vm.expectRevert("EXTERNAL_OPERATOR_DOES_NOT_EXIST");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    "",
                    _subNodeOperators(1, MAX_BP),
                    _externalOperators(
                        _norData(ALLOWED_EXTERNAL_MODULE_ID, EXTERNAL_MODULE_NODE_OPERATORS_COUNT)
                    )
                )
            )
        );
    }

    // python: test_create_group_reverts_with_name_too_long
    function test_RevertWhen_CreatingGroupWithNameTooLong() external {
        vm.expectRevert("GROUP_NAME_TOO_LONG");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                NO_GROUP_ID,
                _group(
                    _name(MAX_NAME_LENGTH + 1), _subNodeOperators(1, MAX_BP), _externalOperators()
                )
            )
        );
    }

    // python: test_create_group_succeeds_with_max_length_name
    function test_CreatesGroupWithMaxLengthName() external view {
        IMetaRegistry.OperatorGroup memory groupInfo =
            _group(_name(MAX_NAME_LENGTH), _subNodeOperators(1, MAX_BP), _externalOperators());

        bytes memory evmScript =
            createOrUpdateOperatorGroup.createEVMScript(owner, _callData(NO_GROUP_ID, groupInfo));

        assertEq(evmScript, _createOrUpdateGroupScript(NO_GROUP_ID, groupInfo), "evmScript");
    }

    // python: test_validate_input_data_reverts_if_current_group_changed
    function test_RevertWhen_ValidatingInputDataAfterCurrentGroupChanged() external {
        metaRegistryStub.createOrUpdateOperatorGroup(
            metaRegistryStub.NO_GROUP_ID(),
            _group("Initial Group", _subNodeOperators(10, MAX_BP), _externalOperators())
        );

        uint256 groupId = metaRegistryStub.getOperatorGroupsCount();
        IMetaRegistry.OperatorGroup memory currentGroupInfo =
            metaRegistryStub.getOperatorGroup(groupId);
        IMetaRegistry.OperatorGroup memory newGroupInfo =
            _group("Updated Group", _subNodeOperators(10, MAX_BP), _externalOperators());

        createOrUpdateOperatorGroup.validateInputData(groupId, currentGroupInfo, newGroupInfo);

        metaRegistryStub.createOrUpdateOperatorGroup(
            groupId, _group("Changed Group", _subNodeOperators(11, MAX_BP), _externalOperators())
        );

        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        createOrUpdateOperatorGroup.validateInputData(groupId, currentGroupInfo, newGroupInfo);
    }

    // python: test_update_group_success
    function test_UpdatesGroup() external {
        metaRegistryStub.setGroupsCount(3);

        IMetaRegistry.OperatorGroup memory groupInfo = _group(
            "Updated Group",
            _subNodeOperators(10, MAX_BP),
            _externalOperators(_norData(ALLOWED_EXTERNAL_MODULE_ID, 1234))
        );

        bytes memory evmScript =
            createOrUpdateOperatorGroup.createEVMScript(owner, _callData(1, groupInfo));

        assertEq(evmScript, _createOrUpdateGroupScript(1, groupInfo), "evmScript");
    }

    // python: test_update_group_reverts_with_name_too_long
    function test_RevertWhen_UpdatingGroupWithNameTooLong() external {
        metaRegistryStub.setGroupsCount(3);

        vm.expectRevert("GROUP_NAME_TOO_LONG");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                1,
                _group(
                    _name(MAX_NAME_LENGTH + 1), _subNodeOperators(10, MAX_BP), _externalOperators()
                )
            )
        );
    }

    // python: test_update_group_clear_success
    function test_ClearsGroup() external {
        metaRegistryStub.setGroupsCount(3);

        bytes memory evmScript =
            createOrUpdateOperatorGroup.createEVMScript(owner, _callData(1, _emptyGroup()));

        assertEq(evmScript, _createOrUpdateGroupScript(1, _emptyGroup()), "evmScript");
    }

    // python: test_update_group_reverts_with_invalid_empty_shape
    function test_RevertWhen_UpdatingGroupWithInvalidEmptyShape() external {
        metaRegistryStub.setGroupsCount(3);

        vm.expectRevert("INVALID_EMPTY_GROUP_UPDATE");
        createOrUpdateOperatorGroup.createEVMScript(
            owner,
            _callData(
                1,
                _group(
                    "",
                    _subNodeOperators(),
                    _externalOperators(_norData(ALLOWED_EXTERNAL_MODULE_ID, 1))
                )
            )
        );
    }

    // python: test_update_group_reverts_with_invalid_group_id[equal_to_groups_count_plus_one]
    function test_RevertWhen_UpdatingGroupWithIdEqualToGroupsCountPlusOne() external {
        metaRegistryStub.setGroupsCount(2);

        vm.expectRevert("INVALID_GROUP_ID");
        createOrUpdateOperatorGroup.createEVMScript(
            owner, _callData(3, _group("", _subNodeOperators(1, MAX_BP), _externalOperators()))
        );
    }

    // python: test_update_group_reverts_with_invalid_group_id[greater_than_groups_count]
    function test_RevertWhen_UpdatingGroupWithIdGreaterThanGroupsCount() external {
        metaRegistryStub.setGroupsCount(2);

        vm.expectRevert("INVALID_GROUP_ID");
        createOrUpdateOperatorGroup.createEVMScript(
            owner, _callData(4, _group("", _subNodeOperators(1, MAX_BP), _externalOperators()))
        );
    }

    // python: test_update_group_reverts_with_invalid_group_id[clear_update]
    function test_RevertWhen_ClearingGroupWithInvalidId() external {
        metaRegistryStub.setGroupsCount(2);

        vm.expectRevert("INVALID_GROUP_ID");
        createOrUpdateOperatorGroup.createEVMScript(owner, _callData(3, _emptyGroup()));
    }

    // python: test_update_group_clear_reverts_with_invalid_group_id_when_no_group_id_is_non_zero
    function test_RevertWhen_ClearingGroupWithInvalidIdAndNonZeroNoGroupId() external {
        metaRegistryStub.setNoGroupId(NON_ZERO_NO_GROUP_ID);
        metaRegistryStub.setGroupsCount(2);

        vm.expectRevert("INVALID_GROUP_ID");
        createOrUpdateOperatorGroup.createEVMScript(owner, _callData(3, _emptyGroup()));
    }

    // python: test_create_and_update_with_non_zero_no_group_id
    function test_CreatesAndUpdatesGroupWithNonZeroNoGroupId() external {
        metaRegistryStub.setNoGroupId(NON_ZERO_NO_GROUP_ID);
        metaRegistryStub.setGroupsCount(12);

        IMetaRegistry.OperatorGroup memory newGroupInfo =
            _group("New Group", _subNodeOperators(1, 6000, 2, 4000), _externalOperators());
        IMetaRegistry.OperatorGroup memory existingGroupInfo =
            _group("Existing Group", _subNodeOperators(3, MAX_BP), _externalOperators());

        bytes memory createScript = createOrUpdateOperatorGroup.createEVMScript(
            owner, _callData(NON_ZERO_NO_GROUP_ID, newGroupInfo)
        );

        assertEq(
            createScript, _createOrUpdateGroupScript(NON_ZERO_NO_GROUP_ID, newGroupInfo), "create"
        );

        bytes memory updateScript =
            createOrUpdateOperatorGroup.createEVMScript(owner, _callData(1, existingGroupInfo));

        assertEq(updateScript, _createOrUpdateGroupScript(1, existingGroupInfo), "update");
    }

    // python: test_update_reverts_with_group_id_beyond_count
    function test_RevertWhen_UpdatingGroupWithIdBeyondCount() external {
        metaRegistryStub.setGroupsCount(2);

        vm.expectRevert("INVALID_GROUP_ID");
        createOrUpdateOperatorGroup.createEVMScript(
            owner, _callData(5, _group("", _subNodeOperators(1, MAX_BP), _externalOperators()))
        );
    }

    function _subNodeOperators() private pure returns (IMetaRegistry.SubNodeOperator[] memory) {
        return new IMetaRegistry.SubNodeOperator[](0);
    }

    function _subNodeOperators(uint64 nodeOperatorId, uint16 share)
        private
        pure
        returns (IMetaRegistry.SubNodeOperator[] memory subNodeOperators)
    {
        subNodeOperators = new IMetaRegistry.SubNodeOperator[](1);
        subNodeOperators[0] =
            IMetaRegistry.SubNodeOperator({nodeOperatorId: nodeOperatorId, share: share});
    }

    function _subNodeOperators(
        uint64 firstNodeOperatorId,
        uint16 firstShare,
        uint64 secondNodeOperatorId,
        uint16 secondShare
    ) private pure returns (IMetaRegistry.SubNodeOperator[] memory subNodeOperators) {
        subNodeOperators = new IMetaRegistry.SubNodeOperator[](2);
        subNodeOperators[0] =
            IMetaRegistry.SubNodeOperator({nodeOperatorId: firstNodeOperatorId, share: firstShare});
        subNodeOperators[1] = IMetaRegistry.SubNodeOperator({
            nodeOperatorId: secondNodeOperatorId, share: secondShare
        });
    }

    function _externalOperators() private pure returns (IMetaRegistry.ExternalOperator[] memory) {
        return new IMetaRegistry.ExternalOperator[](0);
    }

    function _externalOperators(bytes memory data)
        private
        pure
        returns (IMetaRegistry.ExternalOperator[] memory externalOperators)
    {
        externalOperators = new IMetaRegistry.ExternalOperator[](1);
        externalOperators[0] = IMetaRegistry.ExternalOperator({data: data});
    }

    function _externalOperators(bytes memory first, bytes memory second)
        private
        pure
        returns (IMetaRegistry.ExternalOperator[] memory externalOperators)
    {
        externalOperators = new IMetaRegistry.ExternalOperator[](2);
        externalOperators[0] = IMetaRegistry.ExternalOperator({data: first});
        externalOperators[1] = IMetaRegistry.ExternalOperator({data: second});
    }

    /// @dev python: EXT, the ten-byte NOR external operator key
    function _norData(uint256 moduleId, uint256 nodeOperatorId)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(EXT_OPERATOR_TYPE_NOR, uint8(moduleId), uint64(nodeOperatorId));
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

    /// @dev python: empty_group_info
    function _emptyGroup() private pure returns (IMetaRegistry.OperatorGroup memory) {
        return _group("", _subNodeOperators(), _externalOperators());
    }

    /// @dev python: "x" * length
    function _name(uint256 length) private pure returns (string memory) {
        bytes memory name = new bytes(length);

        for (uint256 i; i < length; ++i) {
            name[i] = "x";
        }

        return string(name);
    }

    /// @dev python: C with the default empty currentGroupInfo
    function _callData(uint256 groupId, IMetaRegistry.OperatorGroup memory groupInfo)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(groupId, _emptyGroup(), groupInfo);
    }

    function _assertOperatorGroupEq(
        IMetaRegistry.OperatorGroup memory actual,
        IMetaRegistry.OperatorGroup memory expected,
        string memory label
    ) private pure {
        assertEq(actual.name, expected.name, string(abi.encodePacked(label, " name")));
        assertEq(
            actual.subNodeOperators.length,
            expected.subNodeOperators.length,
            string(abi.encodePacked(label, " subNodeOperators length"))
        );
        assertEq(
            actual.externalOperators.length,
            expected.externalOperators.length,
            string(abi.encodePacked(label, " externalOperators length"))
        );

        for (uint256 i; i < expected.subNodeOperators.length; ++i) {
            assertEq(
                actual.subNodeOperators[i].nodeOperatorId,
                expected.subNodeOperators[i].nodeOperatorId,
                string(abi.encodePacked(label, " nodeOperatorId"))
            );
            assertEq(
                actual.subNodeOperators[i].share,
                expected.subNodeOperators[i].share,
                string(abi.encodePacked(label, " share"))
            );
        }

        for (uint256 i; i < expected.externalOperators.length; ++i) {
            assertEq(
                actual.externalOperators[i].data,
                expected.externalOperators[i].data,
                string(abi.encodePacked(label, " externalOperator data"))
            );
        }
    }

    /// @dev python: S, encode_call_script of validateInputData with the empty current group,
    /// then meta_registry_stub.createOrUpdateOperatorGroup
    function _createOrUpdateGroupScript(
        uint256 groupId,
        IMetaRegistry.OperatorGroup memory groupInfo
    ) private view returns (bytes memory) {
        address[] memory targets = new address[](2);
        targets[0] = address(createOrUpdateOperatorGroup);
        targets[1] = address(metaRegistryStub);

        bytes[] memory datas = new bytes[](2);
        datas[0] = abi.encodeWithSelector(
            ICreateOrUpdateOperatorGroup.validateInputData.selector,
            groupId,
            _emptyGroup(),
            groupInfo
        );
        datas[1] = abi.encodeWithSelector(
            IMetaRegistry.createOrUpdateOperatorGroup.selector, groupId, groupInfo
        );

        return EVMScripts.encodeCallScript(targets, datas);
    }
}
