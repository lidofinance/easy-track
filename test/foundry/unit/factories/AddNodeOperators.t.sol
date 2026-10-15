// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AddNodeOperators} from "contracts/EVMScriptFactories/AddNodeOperators.sol";
import {IACL} from "contracts/interfaces/IACL.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Op, Param, PermissionParameters} from "test/foundry/unit/helpers/PermissionParameters.sol";
import {ACLStub} from "test/foundry/unit/stubs/ACLStub.sol";

contract AddNodeOperatorsTest is Test {
    string internal constant FIRST_OPERATOR_NAME = "Name 1";
    string internal constant SECOND_OPERATOR_NAME = "Name 2";
    address internal constant FIRST_REWARD_ADDRESS = address(1);
    address internal constant SECOND_REWARD_ADDRESS = address(2);
    address internal constant FIRST_MANAGER = address(3);
    address internal constant SECOND_MANAGER = address(4);
    bytes32 internal constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal steth = makeAddr("steth");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    ACLStub internal acl;
    AddNodeOperators internal addNodeOperators;

    function setUp() public {
        nodeOperatorsRegistry = new NodeOperatorsRegistryStub(nodeOperator);
        acl = new ACLStub();

        vm.prank(owner);
        addNodeOperators = new AddNodeOperators(
            owner,
            address(nodeOperatorsRegistry),
            address(acl),
            steth
        );

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(acl), "acl");
        vm.label(address(addNodeOperators), "addNodeOperators");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(addNodeOperators.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(addNodeOperators.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
        assertEq(address(addNodeOperators.acl()), address(acl), "acl");
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        addNodeOperators.createEVMScript(stranger, "");
    }

    // python: test_node_operators_count
    function test_RevertWhen_NodeOperatorsCountMismatches() external {
        vm.expectRevert("NODE_OPERATORS_COUNT_MISMATCH");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(0, _inputs(FIRST_OPERATOR_NAME, FIRST_REWARD_ADDRESS, FIRST_MANAGER))
        );
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(0, new AddNodeOperators.AddNodeOperatorInput[](0))
        );
    }

    // python: test_manager_has_duplicate
    function test_RevertWhen_ManagerAddressesHaveDuplicate() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("MANAGER_ADDRESSES_HAS_DUPLICATE");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(
                nodeOperatorsCount,
                _inputs(
                    FIRST_OPERATOR_NAME,
                    FIRST_REWARD_ADDRESS,
                    FIRST_MANAGER,
                    SECOND_OPERATOR_NAME,
                    SECOND_REWARD_ADDRESS,
                    FIRST_MANAGER
                )
            )
        );
    }

    // python: test_manager_already_has_permission
    function test_RevertWhen_ManagerAlreadyHasPermission() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        acl.grantPermission(
            FIRST_MANAGER,
            address(nodeOperatorsRegistry),
            MANAGE_SIGNING_KEYS_ROLE
        );

        vm.expectRevert("MANAGER_ALREADY_HAS_ROLE");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(
                nodeOperatorsCount,
                _inputs(FIRST_OPERATOR_NAME, FIRST_REWARD_ADDRESS, FIRST_MANAGER)
            )
        );
    }

    // python: test_manager_already_has_permission_for_node_operator
    function test_RevertWhen_ManagerAlreadyHasPermissionForNodeOperator() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        _grantManagerRole(FIRST_MANAGER, Op.EQ, 0);

        vm.expectRevert("MANAGER_ALREADY_HAS_ROLE");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(
                nodeOperatorsCount,
                _inputs(FIRST_OPERATOR_NAME, FIRST_REWARD_ADDRESS, FIRST_MANAGER)
            )
        );
    }

    // python: test_zero_manager
    function test_RevertWhen_ManagerIsZeroAddress() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("ZERO_MANAGER_ADDRESS");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(
                nodeOperatorsCount,
                _inputs(FIRST_OPERATOR_NAME, FIRST_REWARD_ADDRESS, address(0))
            )
        );
    }

    // python: test_zero_reward_address
    function test_RevertWhen_RewardAddressIsZero() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("ZERO_REWARD_ADDRESS");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(
                nodeOperatorsCount,
                _inputs(FIRST_OPERATOR_NAME, address(0), FIRST_MANAGER)
            )
        );
    }

    // python: test_lido_reward_address
    function test_RevertWhen_RewardAddressIsLido() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("LIDO_REWARD_ADDRESS");
        addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(nodeOperatorsCount, _inputs(FIRST_OPERATOR_NAME, steth, FIRST_MANAGER))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        bytes memory evmScript = addNodeOperators.createEVMScript(
            owner,
            _encodeCallData(
                nodeOperatorsCount,
                _inputs(
                    FIRST_OPERATOR_NAME,
                    FIRST_REWARD_ADDRESS,
                    FIRST_MANAGER,
                    SECOND_OPERATOR_NAME,
                    SECOND_REWARD_ADDRESS,
                    SECOND_MANAGER
                )
            )
        );

        address[] memory targets = new address[](4);
        targets[0] = address(nodeOperatorsRegistry);
        targets[1] = address(acl);
        targets[2] = address(nodeOperatorsRegistry);
        targets[3] = address(acl);

        bytes[] memory datas = new bytes[](4);
        datas[0] = _encodeAddNodeOperator(FIRST_OPERATOR_NAME, FIRST_REWARD_ADDRESS);
        datas[1] = _encodeGrantPermissionP(FIRST_MANAGER, nodeOperatorsCount);
        datas[2] = _encodeAddNodeOperator(SECOND_OPERATOR_NAME, SECOND_REWARD_ADDRESS);
        datas[3] = _encodeGrantPermissionP(SECOND_MANAGER, nodeOperatorsCount + 1);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        (
            uint256 decodedCount,
            AddNodeOperators.AddNodeOperatorInput[] memory inputs
        ) = addNodeOperators.decodeEVMScriptCallData(
                _encodeCallData(
                    nodeOperatorsCount,
                    _inputs(
                        FIRST_OPERATOR_NAME,
                        FIRST_REWARD_ADDRESS,
                        FIRST_MANAGER,
                        SECOND_OPERATOR_NAME,
                        SECOND_REWARD_ADDRESS,
                        SECOND_MANAGER
                    )
                )
            );

        assertEq(decodedCount, nodeOperatorsCount, "nodeOperatorsCount");
        assertEq(inputs.length, 2, "inputs length");
        assertEq(inputs[0].name, FIRST_OPERATOR_NAME, "inputs[0].name");
        assertEq(inputs[0].rewardAddress, FIRST_REWARD_ADDRESS, "inputs[0].rewardAddress");
        assertEq(inputs[0].managerAddress, FIRST_MANAGER, "inputs[0].managerAddress");
        assertEq(inputs[1].name, SECOND_OPERATOR_NAME, "inputs[1].name");
        assertEq(inputs[1].rewardAddress, SECOND_REWARD_ADDRESS, "inputs[1].rewardAddress");
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
        string memory name,
        address rewardAddress,
        address manager
    ) private pure returns (AddNodeOperators.AddNodeOperatorInput[] memory inputs) {
        inputs = new AddNodeOperators.AddNodeOperatorInput[](1);
        inputs[0] = AddNodeOperators.AddNodeOperatorInput(name, rewardAddress, manager);
    }

    function _inputs(
        string memory firstName,
        address firstRewardAddress,
        address firstManager,
        string memory secondName,
        address secondRewardAddress,
        address secondManager
    ) private pure returns (AddNodeOperators.AddNodeOperatorInput[] memory inputs) {
        inputs = new AddNodeOperators.AddNodeOperatorInput[](2);
        inputs[0] = AddNodeOperators.AddNodeOperatorInput(
            firstName,
            firstRewardAddress,
            firstManager
        );
        inputs[1] = AddNodeOperators.AddNodeOperatorInput(
            secondName,
            secondRewardAddress,
            secondManager
        );
    }

    function _encodeCallData(
        uint256 nodeOperatorsCount,
        AddNodeOperators.AddNodeOperatorInput[] memory inputs
    ) private pure returns (bytes memory) {
        return abi.encode(nodeOperatorsCount, inputs);
    }

    function _encodeAddNodeOperator(
        string memory name,
        address rewardAddress
    ) private pure returns (bytes memory) {
        return
            abi.encodeWithSelector(
                INodeOperatorsRegistry.addNodeOperator.selector,
                name,
                rewardAddress
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
