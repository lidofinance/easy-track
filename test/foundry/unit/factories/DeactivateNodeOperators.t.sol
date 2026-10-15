// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {DeactivateNodeOperators} from "contracts/EVMScriptFactories/DeactivateNodeOperators.sol";
import {IACL} from "contracts/interfaces/IACL.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Op, Param, PermissionParameters} from "test/foundry/unit/helpers/PermissionParameters.sol";
import {ACLStub} from "test/foundry/unit/stubs/ACLStub.sol";

contract DeactivateNodeOperatorsTest is Test {
    uint256 internal constant NODE_OPERATORS_COUNT = 3;
    /// @dev `setUp` binds the managers to the operators before this one
    uint256 internal constant UNMANAGED_NODE_OPERATOR_ID = 2;
    address internal constant FIRST_MANAGER = address(1);
    address internal constant SECOND_MANAGER = address(2);
    bytes32 internal constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    ACLStub internal acl;
    DeactivateNodeOperators internal deactivateNodeOperators;

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
        deactivateNodeOperators = new DeactivateNodeOperators(
            owner,
            address(nodeOperatorsRegistry),
            address(acl)
        );

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(acl), "acl");
        vm.label(address(deactivateNodeOperators), "deactivateNodeOperators");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(deactivateNodeOperators.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(deactivateNodeOperators.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
        assertEq(address(deactivateNodeOperators.acl()), address(acl), "acl");
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        deactivateNodeOperators.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(new DeactivateNodeOperators.DeactivateNodeOperatorInput[](0))
        );
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreNotSorted() external {
        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(1, SECOND_MANAGER, 0, FIRST_MANAGER))
        );

        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, 0, FIRST_MANAGER))
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_INDEX_OUT_OF_RANGE");
        deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(nodeOperatorsCount, address(0)))
        );
    }

    // python: test_node_operator_invalid_state
    function test_RevertWhen_NodeOperatorIsAlreadyInactive() external {
        nodeOperatorsRegistry.setActive(0, false);

        vm.expectRevert("WRONG_OPERATOR_ACTIVE_STATE");
        deactivateNodeOperators.createEVMScript(owner, _encodeCallData(_inputs(0, FIRST_MANAGER)));
    }

    // python: test_manager_has_no_role
    function test_RevertWhen_ManagerHasNoRole() external {
        vm.expectRevert("MANAGER_HAS_NO_ROLE");
        deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(UNMANAGED_NODE_OPERATOR_ID, FIRST_MANAGER))
        );
    }

    // python: test_manager_has_another_role_operator
    function test_RevertWhen_ManagerRoleExcludesNodeOperator() external {
        _grantManagerRole(FIRST_MANAGER, Op.NEQ, UNMANAGED_NODE_OPERATOR_ID);

        vm.expectRevert("MANAGER_HAS_NO_ROLE");
        deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(UNMANAGED_NODE_OPERATOR_ID, FIRST_MANAGER))
        );
    }

    // python: test_manager_has_role_for_another_operator
    function test_RevertWhen_ManagerHasRoleForAnotherNodeOperator() external {
        _grantManagerRole(FIRST_MANAGER, Op.EQ, UNMANAGED_NODE_OPERATOR_ID + 1);

        vm.expectRevert("MANAGER_HAS_NO_ROLE");
        deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(UNMANAGED_NODE_OPERATOR_ID, FIRST_MANAGER))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = deactivateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, 1, SECOND_MANAGER))
        );

        address[] memory targets = new address[](4);
        targets[0] = address(nodeOperatorsRegistry);
        targets[1] = address(acl);
        targets[2] = address(nodeOperatorsRegistry);
        targets[3] = address(acl);

        bytes[] memory datas = new bytes[](4);
        datas[0] = _encodeDeactivateNodeOperator(0);
        datas[1] = _encodeRevokePermission(FIRST_MANAGER);
        datas[2] = _encodeDeactivateNodeOperator(1);
        datas[3] = _encodeRevokePermission(SECOND_MANAGER);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        DeactivateNodeOperators.DeactivateNodeOperatorInput[]
            memory inputs = deactivateNodeOperators.decodeEVMScriptCallData(
                _encodeCallData(_inputs(0, FIRST_MANAGER, 1, SECOND_MANAGER))
            );

        assertEq(inputs.length, 2, "inputs length");
        assertEq(inputs[0].nodeOperatorId, 0, "inputs[0].nodeOperatorId");
        assertEq(inputs[0].managerAddress, FIRST_MANAGER, "inputs[0].managerAddress");
        assertEq(inputs[1].nodeOperatorId, 1, "inputs[1].nodeOperatorId");
        assertEq(inputs[1].managerAddress, SECOND_MANAGER, "inputs[1].managerAddress");
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
        address manager
    ) private pure returns (DeactivateNodeOperators.DeactivateNodeOperatorInput[] memory inputs) {
        inputs = new DeactivateNodeOperators.DeactivateNodeOperatorInput[](1);
        inputs[0] = DeactivateNodeOperators.DeactivateNodeOperatorInput(nodeOperatorId, manager);
    }

    function _inputs(
        uint256 firstId,
        address firstManager,
        uint256 secondId,
        address secondManager
    ) private pure returns (DeactivateNodeOperators.DeactivateNodeOperatorInput[] memory inputs) {
        inputs = new DeactivateNodeOperators.DeactivateNodeOperatorInput[](2);
        inputs[0] = DeactivateNodeOperators.DeactivateNodeOperatorInput(firstId, firstManager);
        inputs[1] = DeactivateNodeOperators.DeactivateNodeOperatorInput(secondId, secondManager);
    }

    function _encodeCallData(
        DeactivateNodeOperators.DeactivateNodeOperatorInput[] memory inputs
    ) private pure returns (bytes memory) {
        return abi.encode(inputs);
    }

    function _encodeDeactivateNodeOperator(
        uint256 nodeOperatorId
    ) private pure returns (bytes memory) {
        return
            abi.encodeWithSelector(
                INodeOperatorsRegistry.deactivateNodeOperator.selector,
                nodeOperatorId
            );
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
}
