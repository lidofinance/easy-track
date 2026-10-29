// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {RewardProgramsRegistry} from "contracts/RewardProgramsRegistry.sol";
import {EVMScriptCreatorWrapper} from "contracts/test/EVMScriptCreatorWrapper.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract EVMScriptCreatorTest is Test {
    bytes4 internal constant SET_NODE_OPERATOR_STAKING_LIMIT =
        NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector;
    bytes4 internal constant ADD_REWARD_PROGRAM = RewardProgramsRegistry.addRewardProgram.selector;
    bytes4 internal constant REMOVE_REWARD_PROGRAM =
        RewardProgramsRegistry.removeRewardProgram.selector;
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

        address[] memory roleHolders = Arrays.list(voting, address(evmScriptExecutorStub));

        rewardProgramsRegistry = new RewardProgramsRegistry(voting, roleHolders, roleHolders);
        vm.stopPrank();
    }

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

    function test_CreatesEVMScriptForOneAddressMultipleCallsSameMethod() external view {
        bytes[] memory callData = Arrays.list(
            _encodeSetNodeOperatorStakingLimitCallData(1, 300),
            _encodeSetNodeOperatorStakingLimitCallData(2, 500),
            _encodeSetNodeOperatorStakingLimitCallData(3, 600)
        );

        bytes memory evmScript = EVMScriptCreatorWrapper.createEVMScript(
            address(nodeOperatorsRegistryStub), SET_NODE_OPERATOR_STAKING_LIMIT, callData
        );

        bytes memory expected = EVMScripts.encodeCallScript(
            Arrays.list(
                address(nodeOperatorsRegistryStub),
                address(nodeOperatorsRegistryStub),
                address(nodeOperatorsRegistryStub)
            ),
            Arrays.list(
                _setNodeOperatorStakingLimitInput(1, 300),
                _setNodeOperatorStakingLimitInput(2, 500),
                _setNodeOperatorStakingLimitInput(3, 600)
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    function test_RevertWhen_OneAddressMethodIdsAndCallDataLengthsDiffer() external {
        bytes4[] memory methodIds = Arrays.list(SET_NODE_OPERATOR_STAKING_LIMIT);
        bytes[] memory callData = Arrays.list(
            _encodeSetNodeOperatorStakingLimitCallData(1, 300),
            _encodeSetNodeOperatorStakingLimitCallData(1, 300)
        );

        vm.expectRevert("LENGTH_MISMATCH");
        EVMScriptCreatorWrapper.createEVMScript(
            address(nodeOperatorsRegistryStub), methodIds, callData
        );
    }

    function test_CreatesEVMScriptForOneAddressDifferentMethods() external view {
        bytes4[] memory methodIds = Arrays.list(ADD_REWARD_PROGRAM, REMOVE_REWARD_PROGRAM);
        bytes[] memory callData = Arrays.list(
            _encodeAddRewardProgramCallData(rewardProgramToAdd, NEW_REWARD_PROGRAM_TITLE),
            _encodeRemoveRewardProgramCallData(rewardProgramToRemove)
        );

        bytes memory evmScript = EVMScriptCreatorWrapper.createEVMScript(
            address(rewardProgramsRegistry), methodIds, callData
        );

        bytes memory expected = EVMScripts.encodeCallScript(
            Arrays.list(address(rewardProgramsRegistry), address(rewardProgramsRegistry)),
            Arrays.list(
                _addRewardProgramInput(rewardProgramToAdd, NEW_REWARD_PROGRAM_TITLE),
                _removeRewardProgramInput(rewardProgramToRemove)
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    function test_RevertWhen_ManyAddressesLengthsDiffer() external {
        address[] memory targets = Arrays.list(address(nodeOperatorsRegistryStub));
        bytes memory callData = _encodeSetNodeOperatorStakingLimitCallData(1, 300);

        vm.expectRevert("LENGTH_MISMATCH");
        EVMScriptCreatorWrapper.createEVMScript(
            targets,
            Arrays.list(SET_NODE_OPERATOR_STAKING_LIMIT, REMOVE_REWARD_PROGRAM),
            Arrays.list(callData)
        );

        vm.expectRevert("LENGTH_MISMATCH");
        EVMScriptCreatorWrapper.createEVMScript(
            targets, Arrays.list(SET_NODE_OPERATOR_STAKING_LIMIT), Arrays.list(callData, callData)
        );
    }

    function test_CreatesEVMScriptForManyAddresses() external view {
        address[] memory targets = Arrays.list(
            address(nodeOperatorsRegistryStub),
            address(rewardProgramsRegistry),
            address(nodeOperatorsRegistryStub)
        );
        bytes4[] memory methodIds = Arrays.list(
            SET_NODE_OPERATOR_STAKING_LIMIT, REMOVE_REWARD_PROGRAM, SET_NODE_OPERATOR_STAKING_LIMIT
        );
        bytes[] memory callData = Arrays.list(
            _encodeSetNodeOperatorStakingLimitCallData(1, 300),
            _encodeRemoveRewardProgramCallData(rewardProgramToRemove),
            _encodeSetNodeOperatorStakingLimitCallData(3, 600)
        );

        bytes memory evmScript =
            EVMScriptCreatorWrapper.createEVMScript(targets, methodIds, callData);

        bytes memory expected = EVMScripts.encodeCallScript(
            targets,
            Arrays.list(
                _setNodeOperatorStakingLimitInput(1, 300),
                _removeRewardProgramInput(rewardProgramToRemove),
                _setNodeOperatorStakingLimitInput(3, 600)
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    function _encodeSetNodeOperatorStakingLimitCallData(uint256 id, uint256 limit)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(id, limit);
    }

    function _encodeAddRewardProgramCallData(address rewardProgram, string memory title)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(rewardProgram, title);
    }

    function _encodeRemoveRewardProgramCallData(address rewardProgram)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(rewardProgram);
    }

    function _setNodeOperatorStakingLimitInput(uint256 id, uint64 limit)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector, id, limit
        );
    }

    function _addRewardProgramInput(address rewardProgram, string memory title)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            RewardProgramsRegistry.addRewardProgram.selector, rewardProgram, title
        );
    }

    function _removeRewardProgramInput(address rewardProgram) private pure returns (bytes memory) {
        return
            abi.encodeWithSelector(
                RewardProgramsRegistry.removeRewardProgram.selector, rewardProgram
            );
    }
}
