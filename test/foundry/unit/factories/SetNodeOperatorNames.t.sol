// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {SetNodeOperatorNames} from "contracts/EVMScriptFactories/SetNodeOperatorNames.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract SetNodeOperatorNamesTest is Test {
    uint256 internal constant NODE_OPERATORS_COUNT = 2;
    string internal constant NEW_NAME = "New Name";
    string internal constant FIRST_NEW_NAME = "New name";
    string internal constant SECOND_NEW_NAME = "Another Name";

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    SetNodeOperatorNames internal setNodeOperatorNames;

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

        vm.prank(owner);
        setNodeOperatorNames = new SetNodeOperatorNames(owner, address(nodeOperatorsRegistry));

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(setNodeOperatorNames), "setNodeOperatorNames");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(setNodeOperatorNames.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(setNodeOperatorNames.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        setNodeOperatorNames.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        setNodeOperatorNames.createEVMScript(
            owner, _encodeCallData(new SetNodeOperatorNames.SetNameInput[](0))
        );
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreNotSorted() external {
        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        setNodeOperatorNames.createEVMScript(
            owner, _encodeCallData(_inputs(1, NEW_NAME, 0, NEW_NAME))
        );

        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        setNodeOperatorNames.createEVMScript(
            owner, _encodeCallData(_inputs(0, NEW_NAME, 0, NEW_NAME))
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_INDEX_OUT_OF_RANGE");
        setNodeOperatorNames.createEVMScript(
            owner, _encodeCallData(_inputs(nodeOperatorsCount, NEW_NAME))
        );
    }

    // python: test_name_invalid_length
    function test_RevertWhen_NameLengthIsWrong() external {
        vm.expectRevert("WRONG_NAME_LENGTH");
        setNodeOperatorNames.createEVMScript(owner, _encodeCallData(_inputs(0, "")));

        uint256 maxNameLength = nodeOperatorsRegistry.MAX_NODE_OPERATOR_NAME_LENGTH();

        vm.expectRevert("WRONG_NAME_LENGTH");
        setNodeOperatorNames.createEVMScript(
            owner, _encodeCallData(_inputs(0, _nameOfLength(maxNameLength + 1)))
        );
    }

    // python: test_same_name
    function test_RevertWhen_NameIsSame() external {
        (, string memory name,,,,,) = nodeOperatorsRegistry.getNodeOperator(0, true);

        vm.expectRevert("SAME_NAME");
        setNodeOperatorNames.createEVMScript(owner, _encodeCallData(_inputs(0, name)));
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = setNodeOperatorNames.createEVMScript(
            owner, _encodeCallData(_inputs(0, FIRST_NEW_NAME, 1, SECOND_NEW_NAME))
        );

        address[] memory targets = new address[](2);
        targets[0] = address(nodeOperatorsRegistry);
        targets[1] = address(nodeOperatorsRegistry);

        bytes[] memory datas = new bytes[](2);
        datas[0] = _encodeSetNodeOperatorName(0, FIRST_NEW_NAME);
        datas[1] = _encodeSetNodeOperatorName(1, SECOND_NEW_NAME);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        SetNodeOperatorNames.SetNameInput[] memory inputs =
            setNodeOperatorNames.decodeEVMScriptCallData(
                _encodeCallData(_inputs(0, FIRST_NEW_NAME, 1, SECOND_NEW_NAME))
            );

        assertEq(inputs.length, 2, "inputs length");
        assertEq(inputs[0].nodeOperatorId, 0, "inputs[0].nodeOperatorId");
        assertEq(inputs[0].name, FIRST_NEW_NAME, "inputs[0].name");
        assertEq(inputs[1].nodeOperatorId, 1, "inputs[1].nodeOperatorId");
        assertEq(inputs[1].name, SECOND_NEW_NAME, "inputs[1].name");
    }

    function _inputs(uint256 nodeOperatorId, string memory name)
        private
        pure
        returns (SetNodeOperatorNames.SetNameInput[] memory inputs)
    {
        inputs = new SetNodeOperatorNames.SetNameInput[](1);
        inputs[0] = SetNodeOperatorNames.SetNameInput(nodeOperatorId, name);
    }

    function _inputs(
        uint256 firstId,
        string memory firstName,
        uint256 secondId,
        string memory secondName
    ) private pure returns (SetNodeOperatorNames.SetNameInput[] memory inputs) {
        inputs = new SetNodeOperatorNames.SetNameInput[](2);
        inputs[0] = SetNodeOperatorNames.SetNameInput(firstId, firstName);
        inputs[1] = SetNodeOperatorNames.SetNameInput(secondId, secondName);
    }

    /// @dev python: "x" * length
    function _nameOfLength(uint256 length) private pure returns (string memory) {
        bytes memory name = new bytes(length);
        for (uint256 i; i < length; ++i) {
            name[i] = "x";
        }

        return string(name);
    }

    function _encodeCallData(SetNodeOperatorNames.SetNameInput[] memory inputs)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(inputs);
    }

    function _encodeSetNodeOperatorName(uint256 nodeOperatorId, string memory name)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            INodeOperatorsRegistry.setNodeOperatorName.selector, nodeOperatorId, name
        );
    }
}
