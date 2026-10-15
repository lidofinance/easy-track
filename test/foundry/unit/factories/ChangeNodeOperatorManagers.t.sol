// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    ChangeNodeOperatorManagers
} from "contracts/EVMScriptFactories/ChangeNodeOperatorManagers.sol";
import {IACL} from "contracts/interfaces/IACL.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Op, Param, PermissionParameters} from "test/foundry/unit/helpers/PermissionParameters.sol";
import {ACLStub} from "test/foundry/unit/stubs/ACLStub.sol";

contract ChangeNodeOperatorManagersTest is Test {
    uint256 internal constant NODE_OPERATORS_COUNT = 3;
    /// @dev `setUp` binds the managers to the operators before this one
    uint256 internal constant UNMANAGED_NODE_OPERATOR_ID = 2;
    address internal constant FIRST_MANAGER = address(1);
    address internal constant SECOND_MANAGER = address(2);
    address internal constant FIRST_NEW_MANAGER = address(3);
    address internal constant SECOND_NEW_MANAGER = address(4);
    address internal constant ANOTHER_NEW_MANAGER = address(5);
    bytes32 internal constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    ACLStub internal acl;
    ChangeNodeOperatorManagers internal changeNodeOperatorManagers;

    function setUp() public {
        nodeOperatorsRegistry = new NodeOperatorsRegistryStub(nodeOperator);

        for (uint256 i = 1; i < NODE_OPERATORS_COUNT; ++i) {
            nodeOperatorsRegistry.addNodeOperator(
                string(abi.encodePacked("Node Operator ", vm.toString(i))),
                nodeOperator,
                nodeOperatorsRegistry.stakingLimit(),
                nodeOperatorsRegistry.totalSigningKeys()
            );
        }

        acl = new ACLStub();
        _grantManagerRole(FIRST_MANAGER, Op.EQ, 0);
        _grantManagerRole(SECOND_MANAGER, Op.EQ, 1);

        vm.prank(owner);
        changeNodeOperatorManagers = new ChangeNodeOperatorManagers(
            owner,
            address(nodeOperatorsRegistry),
            address(acl)
        );

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(acl), "acl");
        vm.label(address(changeNodeOperatorManagers), "changeNodeOperatorManagers");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(changeNodeOperatorManagers.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(changeNodeOperatorManagers.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        changeNodeOperatorManagers.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(new ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput[](0))
        );
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreNotSorted() external {
        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(
                _inputs(1, SECOND_MANAGER, SECOND_NEW_MANAGER, 0, FIRST_MANAGER, FIRST_NEW_MANAGER)
            )
        );

        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(
                _inputs(0, FIRST_MANAGER, FIRST_NEW_MANAGER, 0, FIRST_MANAGER, SECOND_NEW_MANAGER)
            )
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_INDEX_OUT_OF_RANGE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(nodeOperatorsCount, FIRST_MANAGER, FIRST_NEW_MANAGER))
        );
    }

    // python: test_duplicate_manager
    function test_RevertWhen_NewManagerAddressesHaveDuplicate() external {
        vm.expectRevert("MANAGER_ADDRESSES_HAS_DUPLICATE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(
                _inputs(0, SECOND_MANAGER, SECOND_NEW_MANAGER, 1, FIRST_MANAGER, SECOND_NEW_MANAGER)
            )
        );
    }

    // python: test_manager_has_no_role
    function test_RevertWhen_OldManagerHasNoRole() external {
        vm.expectRevert("OLD_MANAGER_HAS_NO_ROLE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(UNMANAGED_NODE_OPERATOR_ID, FIRST_MANAGER, FIRST_NEW_MANAGER))
        );
    }

    // python: test_manager_has_another_role_operator
    function test_RevertWhen_OldManagerRoleExcludesNodeOperator() external {
        _grantManagerRole(FIRST_MANAGER, Op.NEQ, UNMANAGED_NODE_OPERATOR_ID);

        vm.expectRevert("OLD_MANAGER_HAS_NO_ROLE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(UNMANAGED_NODE_OPERATOR_ID, FIRST_MANAGER, ANOTHER_NEW_MANAGER))
        );
    }

    // python: test_manager_has_role_for_another_operator
    function test_RevertWhen_OldManagerHasRoleForAnotherNodeOperator() external {
        _grantManagerRole(FIRST_MANAGER, Op.EQ, UNMANAGED_NODE_OPERATOR_ID + 1);

        vm.expectRevert("OLD_MANAGER_HAS_NO_ROLE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(UNMANAGED_NODE_OPERATOR_ID, FIRST_MANAGER, ANOTHER_NEW_MANAGER))
        );
    }

    // python: test_old_manager_has_general_permission
    function test_RevertWhen_OldManagerHasGeneralPermission() external {
        acl.grantPermission(
            FIRST_MANAGER,
            address(nodeOperatorsRegistry),
            MANAGE_SIGNING_KEYS_ROLE
        );

        vm.expectRevert("OLD_MANAGER_HAS_NO_ROLE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(UNMANAGED_NODE_OPERATOR_ID, FIRST_MANAGER, ANOTHER_NEW_MANAGER))
        );
    }

    // python: test_zero_manager
    function test_RevertWhen_NewManagerIsZeroAddress() external {
        vm.expectRevert("ZERO_MANAGER_ADDRESS");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, address(0)))
        );
    }

    // python: test_new_manager_has_permission
    function test_RevertWhen_NewManagerHasPermission() external {
        vm.expectRevert("MANAGER_ALREADY_HAS_ROLE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, SECOND_MANAGER))
        );
    }

    // python: test_new_manager_has_general_permission
    function test_RevertWhen_NewManagerHasGeneralPermission() external {
        acl.grantPermission(
            FIRST_NEW_MANAGER,
            address(nodeOperatorsRegistry),
            MANAGE_SIGNING_KEYS_ROLE
        );

        vm.expectRevert("MANAGER_ALREADY_HAS_ROLE");
        changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, FIRST_NEW_MANAGER))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = changeNodeOperatorManagers.createEVMScript(
            owner,
            _encodeCallData(
                _inputs(0, FIRST_MANAGER, FIRST_NEW_MANAGER, 1, SECOND_MANAGER, SECOND_NEW_MANAGER)
            )
        );

        address[] memory targets = new address[](4);
        targets[0] = address(acl);
        targets[1] = address(acl);
        targets[2] = address(acl);
        targets[3] = address(acl);

        bytes[] memory datas = new bytes[](4);
        datas[0] = _encodeRevokePermission(FIRST_MANAGER);
        datas[1] = _encodeGrantPermissionP(FIRST_NEW_MANAGER, 0);
        datas[2] = _encodeRevokePermission(SECOND_MANAGER);
        datas[3] = _encodeGrantPermissionP(SECOND_NEW_MANAGER, 1);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput[]
            memory inputs = changeNodeOperatorManagers.decodeEVMScriptCallData(
                _encodeCallData(
                    _inputs(
                        0,
                        FIRST_MANAGER,
                        FIRST_NEW_MANAGER,
                        1,
                        SECOND_MANAGER,
                        SECOND_NEW_MANAGER
                    )
                )
            );

        assertEq(inputs.length, 2, "inputs length");
        assertEq(inputs[0].nodeOperatorId, 0, "inputs[0].nodeOperatorId");
        assertEq(inputs[0].oldManagerAddress, FIRST_MANAGER, "inputs[0].oldManagerAddress");
        assertEq(inputs[0].newManagerAddress, FIRST_NEW_MANAGER, "inputs[0].newManagerAddress");
        assertEq(inputs[1].nodeOperatorId, 1, "inputs[1].nodeOperatorId");
        assertEq(inputs[1].oldManagerAddress, SECOND_MANAGER, "inputs[1].oldManagerAddress");
        assertEq(inputs[1].newManagerAddress, SECOND_NEW_MANAGER, "inputs[1].newManagerAddress");
    }

    /// @dev python: acl.grantPermissionP(manager, registry, MANAGE_SIGNING_KEYS_ROLE,
    /// encode_permission_params([Param(0, op, value)]))
    function _grantManagerRole(address manager, Op op, uint256 value) private {
        acl.grantPermissionP(
            manager,
            address(nodeOperatorsRegistry),
            MANAGE_SIGNING_KEYS_ROLE,
            PermissionParameters.encodePermissionParams(Param(0, op, value))
        );
    }

    function _inputs(
        uint256 nodeOperatorId,
        address oldManager,
        address newManager
    )
        private
        pure
        returns (ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput[] memory inputs)
    {
        inputs = new ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput[](1);
        inputs[0] = ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput(
            nodeOperatorId,
            oldManager,
            newManager
        );
    }

    function _inputs(
        uint256 firstId,
        address firstOldManager,
        address firstNewManager,
        uint256 secondId,
        address secondOldManager,
        address secondNewManager
    )
        private
        pure
        returns (ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput[] memory inputs)
    {
        inputs = new ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput[](2);
        inputs[0] = ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput(
            firstId,
            firstOldManager,
            firstNewManager
        );
        inputs[1] = ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput(
            secondId,
            secondOldManager,
            secondNewManager
        );
    }

    function _encodeCallData(
        ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput[] memory inputs
    ) private pure returns (bytes memory) {
        return abi.encode(inputs);
    }

    function _encodeRevokePermission(address manager) private view returns (bytes memory) {
        return
            abi.encodeWithSelector(
                IACL.revokePermission.selector,
                manager,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE
            );
    }

    /// @dev The manager's role is bound to `nodeOperatorId`, the first argument of every guarded call
    function _encodeGrantPermissionP(
        address manager,
        uint256 nodeOperatorId
    ) private view returns (bytes memory) {
        return
            abi.encodeWithSelector(
                IACL.grantPermissionP.selector,
                manager,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE,
                PermissionParameters.encodePermissionParams(Param(0, Op.EQ, nodeOperatorId))
            );
    }
}
