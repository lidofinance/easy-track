// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {ActivateNodeOperators} from "contracts/EVMScriptFactories/ActivateNodeOperators.sol";
import {IACL} from "contracts/interfaces/IACL.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Op, Param, PermissionParameters} from "test/foundry/unit/helpers/PermissionParameters.sol";
import {ACLStub} from "test/foundry/unit/stubs/ACLStub.sol";

contract ActivateNodeOperatorsTest is Test {
    uint256 internal constant NODE_OPERATORS_COUNT = 3;
    /// @dev `setUp` deactivates the operators before this one
    uint256 internal constant ACTIVE_NODE_OPERATOR_ID = 2;
    address internal constant FIRST_MANAGER = address(1);
    address internal constant SECOND_MANAGER = address(2);
    bytes32 internal constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    ACLStub internal acl;
    ActivateNodeOperators internal activateNodeOperators;

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

        vm.prank(owner);
        activateNodeOperators = new ActivateNodeOperators(
            owner,
            address(nodeOperatorsRegistry),
            address(acl)
        );

        nodeOperatorsRegistry.setActive(0, false);
        nodeOperatorsRegistry.setActive(1, false);

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(acl), "acl");
        vm.label(address(activateNodeOperators), "activateNodeOperators");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(activateNodeOperators.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(activateNodeOperators.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
        assertEq(address(activateNodeOperators.acl()), address(acl), "acl");
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        activateNodeOperators.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        activateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(new ActivateNodeOperators.ActivateNodeOperatorInput[](0))
        );
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreNotSorted() external {
        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        activateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(1, SECOND_MANAGER, 0, FIRST_MANAGER))
        );

        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        activateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, 0, SECOND_MANAGER))
        );
    }

    // python: test_manager_has_duplicates
    function test_RevertWhen_ManagerAddressesHaveDuplicate() external {
        vm.expectRevert("MANAGER_ADDRESSES_HAS_DUPLICATE");
        activateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, 1, FIRST_MANAGER))
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_INDEX_OUT_OF_RANGE");
        activateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(nodeOperatorsCount, address(0)))
        );
    }

    // python: test_node_operator_invalid_state
    function test_RevertWhen_NodeOperatorIsAlreadyActive() external {
        vm.expectRevert("WRONG_OPERATOR_ACTIVE_STATE");
        activateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(ACTIVE_NODE_OPERATOR_ID, FIRST_MANAGER))
        );
    }

    // python: test_manager_already_has_permission
    function test_RevertWhen_ManagerAlreadyHasPermission() external {
        acl.grantPermission(
            FIRST_MANAGER,
            address(nodeOperatorsRegistry),
            MANAGE_SIGNING_KEYS_ROLE
        );

        vm.expectRevert("MANAGER_ALREADY_HAS_ROLE");
        activateNodeOperators.createEVMScript(owner, _encodeCallData(_inputs(0, FIRST_MANAGER)));
    }

    // python: test_manager_already_has_permission_for_node_operator
    function test_RevertWhen_ManagerAlreadyHasPermissionForNodeOperator() external {
        _grantManagerRole(FIRST_MANAGER, Op.EQ, 0);

        vm.expectRevert("MANAGER_ALREADY_HAS_ROLE");
        activateNodeOperators.createEVMScript(owner, _encodeCallData(_inputs(0, FIRST_MANAGER)));
    }

    // python: test_manager_already_has_permission_for_different_node_operator
    function test_RevertWhen_ManagerAlreadyHasPermissionForDifferentNodeOperator() external {
        _grantManagerRole(FIRST_MANAGER, Op.EQ, 1);

        vm.expectRevert("MANAGER_ALREADY_HAS_ROLE");
        activateNodeOperators.createEVMScript(owner, _encodeCallData(_inputs(0, FIRST_MANAGER)));
    }

    // python: test_zero_manager
    function test_RevertWhen_ManagerIsZeroAddress() external {
        vm.expectRevert("ZERO_MANAGER_ADDRESS");
        activateNodeOperators.createEVMScript(owner, _encodeCallData(_inputs(0, address(0))));
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = activateNodeOperators.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_MANAGER, 1, SECOND_MANAGER))
        );

        address[] memory targets = new address[](4);
        targets[0] = address(nodeOperatorsRegistry);
        targets[1] = address(acl);
        targets[2] = address(nodeOperatorsRegistry);
        targets[3] = address(acl);

        bytes[] memory datas = new bytes[](4);
        datas[0] = _encodeActivateNodeOperator(0);
        datas[1] = _encodeGrantPermissionP(FIRST_MANAGER, 0);
        datas[2] = _encodeActivateNodeOperator(1);
        datas[3] = _encodeGrantPermissionP(SECOND_MANAGER, 1);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        ActivateNodeOperators.ActivateNodeOperatorInput[] memory inputs = activateNodeOperators
            .decodeEVMScriptCallData(_encodeCallData(_inputs(0, FIRST_MANAGER, 1, SECOND_MANAGER)));

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
    ) private pure returns (ActivateNodeOperators.ActivateNodeOperatorInput[] memory inputs) {
        inputs = new ActivateNodeOperators.ActivateNodeOperatorInput[](1);
        inputs[0] = ActivateNodeOperators.ActivateNodeOperatorInput(nodeOperatorId, manager);
    }

    function _inputs(
        uint256 firstId,
        address firstManager,
        uint256 secondId,
        address secondManager
    ) private pure returns (ActivateNodeOperators.ActivateNodeOperatorInput[] memory inputs) {
        inputs = new ActivateNodeOperators.ActivateNodeOperatorInput[](2);
        inputs[0] = ActivateNodeOperators.ActivateNodeOperatorInput(firstId, firstManager);
        inputs[1] = ActivateNodeOperators.ActivateNodeOperatorInput(secondId, secondManager);
    }

    function _encodeCallData(
        ActivateNodeOperators.ActivateNodeOperatorInput[] memory inputs
    ) private pure returns (bytes memory) {
        return abi.encode(inputs);
    }

    function _encodeActivateNodeOperator(
        uint256 nodeOperatorId
    ) private pure returns (bytes memory) {
        return
            abi.encodeWithSelector(
                INodeOperatorsRegistry.activateNodeOperator.selector,
                nodeOperatorId
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
