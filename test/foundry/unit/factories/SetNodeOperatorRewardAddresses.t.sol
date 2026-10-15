// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SetNodeOperatorRewardAddresses
} from "contracts/EVMScriptFactories/SetNodeOperatorRewardAddresses.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract SetNodeOperatorRewardAddressesTest is Test {
    uint256 internal constant NODE_OPERATORS_COUNT = 2;
    address internal constant FIRST_NEW_REWARD_ADDRESS = address(1);
    address internal constant SECOND_NEW_REWARD_ADDRESS = address(2);

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal steth = makeAddr("steth");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    SetNodeOperatorRewardAddresses internal setNodeOperatorRewardAddresses;

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
        setNodeOperatorRewardAddresses =
            new SetNodeOperatorRewardAddresses(owner, address(nodeOperatorsRegistry), steth);

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(setNodeOperatorRewardAddresses), "setNodeOperatorRewardAddresses");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(setNodeOperatorRewardAddresses.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(setNodeOperatorRewardAddresses.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        setNodeOperatorRewardAddresses.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        setNodeOperatorRewardAddresses.createEVMScript(
            owner, _encodeCallData(new SetNodeOperatorRewardAddresses.SetRewardAddressInput[](0))
        );
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreNotSorted() external {
        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        setNodeOperatorRewardAddresses.createEVMScript(
            owner,
            _encodeCallData(_inputs(1, SECOND_NEW_REWARD_ADDRESS, 0, FIRST_NEW_REWARD_ADDRESS))
        );

        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        setNodeOperatorRewardAddresses.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_NEW_REWARD_ADDRESS, 0, FIRST_NEW_REWARD_ADDRESS))
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_INDEX_OUT_OF_RANGE");
        setNodeOperatorRewardAddresses.createEVMScript(
            owner, _encodeCallData(_inputs(nodeOperatorsCount, FIRST_NEW_REWARD_ADDRESS))
        );
    }

    // python: test_same_reward_address
    function test_RevertWhen_RewardAddressIsSame() external {
        (,, address rewardAddress,,,,) = nodeOperatorsRegistry.getNodeOperator(0, true);

        vm.expectRevert("SAME_REWARD_ADDRESS");
        setNodeOperatorRewardAddresses.createEVMScript(
            owner, _encodeCallData(_inputs(0, rewardAddress))
        );
    }

    // python: test_zero_reward_address
    function test_RevertWhen_RewardAddressIsZero() external {
        vm.expectRevert("ZERO_REWARD_ADDRESS");
        setNodeOperatorRewardAddresses.createEVMScript(
            owner, _encodeCallData(_inputs(0, address(0)))
        );
    }

    // python: test_lido_as_reward_address
    function test_RevertWhen_RewardAddressIsLido() external {
        vm.expectRevert("LIDO_REWARD_ADDRESS");
        setNodeOperatorRewardAddresses.createEVMScript(owner, _encodeCallData(_inputs(0, steth)));
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = setNodeOperatorRewardAddresses.createEVMScript(
            owner,
            _encodeCallData(_inputs(0, FIRST_NEW_REWARD_ADDRESS, 1, SECOND_NEW_REWARD_ADDRESS))
        );

        address[] memory targets = new address[](2);
        targets[0] = address(nodeOperatorsRegistry);
        targets[1] = address(nodeOperatorsRegistry);

        bytes[] memory datas = new bytes[](2);
        datas[0] = _encodeSetNodeOperatorRewardAddress(0, FIRST_NEW_REWARD_ADDRESS);
        datas[1] = _encodeSetNodeOperatorRewardAddress(1, SECOND_NEW_REWARD_ADDRESS);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        SetNodeOperatorRewardAddresses.SetRewardAddressInput[] memory inputs =
            setNodeOperatorRewardAddresses.decodeEVMScriptCallData(
                _encodeCallData(_inputs(0, FIRST_NEW_REWARD_ADDRESS, 1, SECOND_NEW_REWARD_ADDRESS))
            );

        assertEq(inputs.length, 2, "inputs length");
        assertEq(inputs[0].nodeOperatorId, 0, "inputs[0].nodeOperatorId");
        assertEq(inputs[0].rewardAddress, FIRST_NEW_REWARD_ADDRESS, "inputs[0].rewardAddress");
        assertEq(inputs[1].nodeOperatorId, 1, "inputs[1].nodeOperatorId");
        assertEq(inputs[1].rewardAddress, SECOND_NEW_REWARD_ADDRESS, "inputs[1].rewardAddress");
    }

    function _inputs(uint256 nodeOperatorId, address rewardAddress)
        private
        pure
        returns (SetNodeOperatorRewardAddresses.SetRewardAddressInput[] memory inputs)
    {
        inputs = new SetNodeOperatorRewardAddresses.SetRewardAddressInput[](1);
        inputs[0] =
            SetNodeOperatorRewardAddresses.SetRewardAddressInput(nodeOperatorId, rewardAddress);
    }

    function _inputs(
        uint256 firstId,
        address firstRewardAddress,
        uint256 secondId,
        address secondRewardAddress
    ) private pure returns (SetNodeOperatorRewardAddresses.SetRewardAddressInput[] memory inputs) {
        inputs = new SetNodeOperatorRewardAddresses.SetRewardAddressInput[](2);
        inputs[0] =
            SetNodeOperatorRewardAddresses.SetRewardAddressInput(firstId, firstRewardAddress);
        inputs[1] =
            SetNodeOperatorRewardAddresses.SetRewardAddressInput(secondId, secondRewardAddress);
    }

    function _encodeCallData(SetNodeOperatorRewardAddresses.SetRewardAddressInput[] memory inputs)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(inputs);
    }

    function _encodeSetNodeOperatorRewardAddress(uint256 nodeOperatorId, address rewardAddress)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            INodeOperatorsRegistry.setNodeOperatorRewardAddress.selector,
            nodeOperatorId,
            rewardAddress
        );
    }
}
