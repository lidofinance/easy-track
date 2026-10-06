// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {RemoveRewardProgram} from "contracts/EVMScriptFactories/RemoveRewardProgram.sol";
import {RewardProgramsRegistry} from "contracts/RewardProgramsRegistry.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract RemoveRewardProgramTest is Test {
    address internal constant REWARD_PROGRAM_ADDRESS = 0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");

    EVMScriptExecutorStub internal evmScriptExecutorStub;
    RewardProgramsRegistry internal rewardProgramsRegistry;
    RemoveRewardProgram internal removeRewardProgram;

    function setUp() public {
        vm.startPrank(owner);
        evmScriptExecutorStub = new EVMScriptExecutorStub();
        rewardProgramsRegistry = new RewardProgramsRegistry(voting, _roleHolders(), _roleHolders());
        removeRewardProgram = new RemoveRewardProgram(owner, address(rewardProgramsRegistry));
        vm.stopPrank();

        vm.label(address(evmScriptExecutorStub), "evmScriptExecutorStub");
        vm.label(address(rewardProgramsRegistry), "rewardProgramsRegistry");
        vm.label(address(removeRewardProgram), "removeRewardProgram");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(removeRewardProgram.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(removeRewardProgram.rewardProgramsRegistry()),
            address(rewardProgramsRegistry),
            "rewardProgramsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        removeRewardProgram.createEVMScript(stranger, _encodeCallData());
    }

    // python: test_create_evm_script_reward_program_already_added
    function test_RevertWhen_RewardProgramNotFound() external {
        vm.expectRevert("REWARD_PROGRAM_NOT_FOUND");
        removeRewardProgram.createEVMScript(owner, _encodeCallData());
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        vm.prank(address(evmScriptExecutorStub));
        rewardProgramsRegistry.addRewardProgram(REWARD_PROGRAM_ADDRESS, "");

        bytes memory evmScript = removeRewardProgram.createEVMScript(owner, _encodeCallData());

        bytes memory expected = EVMScripts.encodeCallScript(
            address(rewardProgramsRegistry),
            abi.encodeWithSelector(
                RewardProgramsRegistry.removeRewardProgram.selector, REWARD_PROGRAM_ADDRESS
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address rewardProgram = removeRewardProgram.decodeEVMScriptCallData(_encodeCallData());

        assertEq(rewardProgram, REWARD_PROGRAM_ADDRESS, "rewardProgram");
    }

    function _roleHolders() private view returns (address[] memory holders) {
        holders = new address[](2);
        holders[0] = voting;
        holders[1] = address(evmScriptExecutorStub);
    }

    function _encodeCallData() private pure returns (bytes memory) {
        return abi.encode(REWARD_PROGRAM_ADDRESS);
    }
}
