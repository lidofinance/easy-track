// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {RewardProgramsRegistry} from "contracts/RewardProgramsRegistry.sol";
import {EVMScriptCreatorWrapper} from "contracts/test/EVMScriptCreatorWrapper.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract EVMScriptCreatorTest is Test {
    bytes4 internal constant SET_NODE_OPERATOR_STAKING_LIMIT = 0xae962acf;
    bytes4 internal constant ADD_REWARD_PROGRAM = 0xfa508cef;
    bytes4 internal constant REMOVE_REWARD_PROGRAM = 0x945233e2;
    string internal constant NEW_REWARD_PROGRAM_TITLE = "new reward program";

    address internal owner = makeAddr("owner");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal voting = makeAddr("voting");
    address internal rewardProgramToAdd = makeAddr("rewardProgramToAdd");
    address internal rewardProgramToRemove = makeAddr("rewardProgramToRemove");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistryStub;
    RewardProgramsRegistry internal rewardProgramsRegistry;

    function setUp() public {
        vm.startPrank(owner);
        nodeOperatorsRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);
        EVMScriptExecutorStub evmScriptExecutorStub = new EVMScriptExecutorStub();

        address[] memory roleHolders = new address[](2);
        roleHolders[0] = voting;
        roleHolders[1] = address(evmScriptExecutorStub);

        rewardProgramsRegistry = new RewardProgramsRegistry(voting, roleHolders, roleHolders);
        vm.stopPrank();
    }

    // python: test_create_evm_script_one_address_single_call
    function test_CreatesEVMScriptForOneAddressSingleCall() external view {
        bytes memory evmScript = EVMScriptCreatorWrapper.createEVMScript(
            address(nodeOperatorsRegistryStub),
            SET_NODE_OPERATOR_STAKING_LIMIT,
            _encodeSetNodeOperatorStakingLimitCallData(1, 300)
        );

        bytes memory expected = EVMScripts.encodeCallScript(
            address(nodeOperatorsRegistryStub), _setNodeOperatorStakingLimitInput(1, 300)
        );

        assertEq(evmScript, expected, "evmScript");
    }

    // python: test_create_evm_script_one_address_multiple_calls_same_method
    function test_CreatesEVMScriptForOneAddressMultipleCallsSameMethod() external view {
        bytes[] memory callData = _list(
            _encodeSetNodeOperatorStakingLimitCallData(1, 300),
            _encodeSetNodeOperatorStakingLimitCallData(2, 500),
            _encodeSetNodeOperatorStakingLimitCallData(3, 600)
        );

        bytes memory evmScript = EVMScriptCreatorWrapper.createEVMScript(
            address(nodeOperatorsRegistryStub), SET_NODE_OPERATOR_STAKING_LIMIT, callData
        );

        bytes memory expected = EVMScripts.encodeCallScript(
            _list(
                address(nodeOperatorsRegistryStub),
                address(nodeOperatorsRegistryStub),
                address(nodeOperatorsRegistryStub)
            ),
            _list(
                _setNodeOperatorStakingLimitInput(1, 300),
                _setNodeOperatorStakingLimitInput(2, 500),
                _setNodeOperatorStakingLimitInput(3, 600)
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    // python: test_create_evm_script_one_address_different_methods_different_lengths
    function test_RevertWhen_OneAddressMethodIdsAndCallDataLengthsDiffer() external {
        bytes4[] memory methodIds = _list(SET_NODE_OPERATOR_STAKING_LIMIT);
        bytes[] memory callData = _list(
            _encodeSetNodeOperatorStakingLimitCallData(1, 300),
            _encodeSetNodeOperatorStakingLimitCallData(1, 300)
        );

        vm.expectRevert("LENGTH_MISMATCH");
        EVMScriptCreatorWrapper.createEVMScript(
            address(nodeOperatorsRegistryStub), methodIds, callData
        );
    }

    // python: test_create_evm_script_one_address_different_methods
    function test_CreatesEVMScriptForOneAddressDifferentMethods() external view {
        bytes4[] memory methodIds = _list(ADD_REWARD_PROGRAM, REMOVE_REWARD_PROGRAM);
        bytes[] memory callData = _list(
            _encodeAddRewardProgramCallData(rewardProgramToAdd, NEW_REWARD_PROGRAM_TITLE),
            _encodeRemoveRewardProgramCallData(rewardProgramToRemove)
        );

        bytes memory evmScript = EVMScriptCreatorWrapper.createEVMScript(
            address(rewardProgramsRegistry), methodIds, callData
        );

        bytes memory expected = EVMScripts.encodeCallScript(
            _list(address(rewardProgramsRegistry), address(rewardProgramsRegistry)),
            _list(
                _addRewardProgramInput(rewardProgramToAdd, NEW_REWARD_PROGRAM_TITLE),
                _removeRewardProgramInput(rewardProgramToRemove)
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    // python: test_create_evm_script_many_addresses_different_lengths
    function test_RevertWhen_ManyAddressesLengthsDiffer() external {
        address[] memory targets = _list(address(nodeOperatorsRegistryStub));
        bytes memory callData = _encodeSetNodeOperatorStakingLimitCallData(1, 300);

        vm.expectRevert("LENGTH_MISMATCH");
        EVMScriptCreatorWrapper.createEVMScript(
            targets, _list(SET_NODE_OPERATOR_STAKING_LIMIT, REMOVE_REWARD_PROGRAM), _list(callData)
        );

        vm.expectRevert("LENGTH_MISMATCH");
        EVMScriptCreatorWrapper.createEVMScript(
            targets, _list(SET_NODE_OPERATOR_STAKING_LIMIT), _list(callData, callData)
        );
    }

    // python: test_create_evm_script_many_addresses
    function test_CreatesEVMScriptForManyAddresses() external view {
        address[] memory targets = _list(
            address(nodeOperatorsRegistryStub),
            address(rewardProgramsRegistry),
            address(nodeOperatorsRegistryStub)
        );
        bytes4[] memory methodIds = _list(
            SET_NODE_OPERATOR_STAKING_LIMIT, REMOVE_REWARD_PROGRAM, SET_NODE_OPERATOR_STAKING_LIMIT
        );
        bytes[] memory callData = _list(
            _encodeSetNodeOperatorStakingLimitCallData(1, 300),
            _encodeRemoveRewardProgramCallData(rewardProgramToRemove),
            _encodeSetNodeOperatorStakingLimitCallData(3, 600)
        );

        bytes memory evmScript =
            EVMScriptCreatorWrapper.createEVMScript(targets, methodIds, callData);

        bytes memory expected = EVMScripts.encodeCallScript(
            targets,
            _list(
                _setNodeOperatorStakingLimitInput(1, 300),
                _removeRewardProgramInput(rewardProgramToRemove),
                _setNodeOperatorStakingLimitInput(3, 600)
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    // python: encode_set_node_operator_staking_limit_calldata, encoded as (uint256,uint256)
    function _encodeSetNodeOperatorStakingLimitCallData(uint256 id, uint256 limit)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(id, limit);
    }

    // python: encode_add_reward_program_calldata
    function _encodeAddRewardProgramCallData(address rewardProgram, string memory title)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(rewardProgram, title);
    }

    // python: encode_remove_reward_program_calldata
    function _encodeRemoveRewardProgramCallData(address rewardProgram)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(rewardProgram);
    }

    // python: node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input
    function _setNodeOperatorStakingLimitInput(uint256 id, uint64 limit)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector, id, limit
        );
    }

    // python: reward_programs_registry.addRewardProgram.encode_input
    function _addRewardProgramInput(address rewardProgram, string memory title)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            RewardProgramsRegistry.addRewardProgram.selector, rewardProgram, title
        );
    }

    // python: reward_programs_registry.removeRewardProgram.encode_input
    function _removeRewardProgramInput(address rewardProgram) private pure returns (bytes memory) {
        return
            abi.encodeWithSelector(
                RewardProgramsRegistry.removeRewardProgram.selector, rewardProgram
            );
    }

    function _list(address a) private pure returns (address[] memory list) {
        list = new address[](1);
        list[0] = a;
    }

    function _list(address a, address b) private pure returns (address[] memory list) {
        list = new address[](2);
        list[0] = a;
        list[1] = b;
    }

    function _list(address a, address b, address c) private pure returns (address[] memory list) {
        list = new address[](3);
        list[0] = a;
        list[1] = b;
        list[2] = c;
    }

    function _list(bytes4 a) private pure returns (bytes4[] memory list) {
        list = new bytes4[](1);
        list[0] = a;
    }

    function _list(bytes4 a, bytes4 b) private pure returns (bytes4[] memory list) {
        list = new bytes4[](2);
        list[0] = a;
        list[1] = b;
    }

    function _list(bytes4 a, bytes4 b, bytes4 c) private pure returns (bytes4[] memory list) {
        list = new bytes4[](3);
        list[0] = a;
        list[1] = b;
        list[2] = c;
    }

    function _list(bytes memory a) private pure returns (bytes[] memory list) {
        list = new bytes[](1);
        list[0] = a;
    }

    function _list(bytes memory a, bytes memory b) private pure returns (bytes[] memory list) {
        list = new bytes[](2);
        list[0] = a;
        list[1] = b;
    }

    function _list(bytes memory a, bytes memory b, bytes memory c)
        private
        pure
        returns (bytes[] memory list)
    {
        list = new bytes[](3);
        list[0] = a;
        list[1] = b;
        list[2] = c;
    }
}
