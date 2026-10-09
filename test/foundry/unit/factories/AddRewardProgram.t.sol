// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AddRewardProgram} from "contracts/EVMScriptFactories/AddRewardProgram.sol";
import {RewardProgramsRegistry} from "contracts/RewardProgramsRegistry.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract AddRewardProgramTest is Test {
    address internal constant REWARD_PROGRAM_ADDRESS = 0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF;
    string internal constant REWARD_PROGRAM_TITLE = "New Reward Program";

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");

    EVMScriptExecutorStub internal evmScriptExecutorStub;
    RewardProgramsRegistry internal rewardProgramsRegistry;
    AddRewardProgram internal addRewardProgram;

    function setUp() public {
        vm.startPrank(owner);
        evmScriptExecutorStub = new EVMScriptExecutorStub();
        rewardProgramsRegistry = new RewardProgramsRegistry(voting, _roleHolders(), _roleHolders());
        addRewardProgram = new AddRewardProgram(owner, address(rewardProgramsRegistry));
        vm.stopPrank();

        vm.label(address(evmScriptExecutorStub), "evmScriptExecutorStub");
        vm.label(address(rewardProgramsRegistry), "rewardProgramsRegistry");
        vm.label(address(addRewardProgram), "addRewardProgram");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(addRewardProgram.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(addRewardProgram.rewardProgramsRegistry()),
            address(rewardProgramsRegistry),
            "rewardProgramsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        addRewardProgram.createEVMScript(stranger, _encodeCallData());
    }

    // python: test_create_evm_script_reward_program_already_added
    function test_RevertWhen_RewardProgramAlreadyAdded() external {
        vm.prank(address(evmScriptExecutorStub));
        rewardProgramsRegistry.addRewardProgram(REWARD_PROGRAM_ADDRESS, REWARD_PROGRAM_TITLE);

        assertTrue(
            rewardProgramsRegistry.isRewardProgram(REWARD_PROGRAM_ADDRESS), "isRewardProgram"
        );

        vm.expectRevert("REWARD_PROGRAM_ALREADY_ADDED");
        addRewardProgram.createEVMScript(owner, _encodeCallData());
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = addRewardProgram.createEVMScript(owner, _encodeCallData());

        bytes memory expected = EVMScripts.encodeCallScript(
            address(rewardProgramsRegistry),
            abi.encodeWithSelector(
                RewardProgramsRegistry.addRewardProgram.selector,
                REWARD_PROGRAM_ADDRESS,
                REWARD_PROGRAM_TITLE
            )
        );

        assertEq(evmScript, expected, "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        (address rewardProgram, string memory title) =
            addRewardProgram.decodeEVMScriptCallData(_encodeCallData());

        assertEq(rewardProgram, REWARD_PROGRAM_ADDRESS, "rewardProgram");
        assertEq(title, REWARD_PROGRAM_TITLE, "title");
    }

    function _roleHolders() private view returns (address[] memory holders) {
        holders = new address[](2);
        holders[0] = voting;
        holders[1] = address(evmScriptExecutorStub);
    }

    function _encodeCallData() private pure returns (bytes memory) {
        return abi.encode(REWARD_PROGRAM_ADDRESS, REWARD_PROGRAM_TITLE);
    }
}
