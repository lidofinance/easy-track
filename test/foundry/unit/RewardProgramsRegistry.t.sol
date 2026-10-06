// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {RewardProgramsRegistry} from "contracts/RewardProgramsRegistry.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {TestHelpers} from "test/foundry/unit/helpers/TestHelpers.sol";

contract RewardProgramsRegistryTest is Test {
    string internal constant REWARD_PROGRAM_TITLE = "Reward Program";
    uint256 internal constant REWARD_PROGRAMS_COUNT = 5;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");
    address internal rewardProgram = makeAddr("rewardProgram");

    EVMScriptExecutorStub internal evmScriptExecutorStub;
    RewardProgramsRegistry internal rewardProgramsRegistry;

    event RewardProgramAdded(address indexed _rewardProgram, string _title);
    event RewardProgramRemoved(address indexed _rewardProgram);

    function setUp() public {
        vm.startPrank(owner);
        evmScriptExecutorStub = new EVMScriptExecutorStub();
        rewardProgramsRegistry = new RewardProgramsRegistry(voting, _roleHolders(), _roleHolders());
        vm.stopPrank();

        vm.label(address(evmScriptExecutorStub), "evmScriptExecutorStub");
        vm.label(address(rewardProgramsRegistry), "rewardProgramsRegistry");
    }

    // python: test_deploy
    function test_Deploy() external view {
        bytes32 addRole = rewardProgramsRegistry.ADD_REWARD_PROGRAM_ROLE();
        bytes32 removeRole = rewardProgramsRegistry.REMOVE_REWARD_PROGRAM_ROLE();

        assertTrue(
            rewardProgramsRegistry.hasRole(rewardProgramsRegistry.DEFAULT_ADMIN_ROLE(), voting),
            "voting DEFAULT_ADMIN_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(addRole, voting), "voting ADD_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(removeRole, voting), "voting REMOVE_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(addRole, address(evmScriptExecutorStub)),
            "evmScriptExecutorStub ADD_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(removeRole, address(evmScriptExecutorStub)),
            "evmScriptExecutorStub REMOVE_REWARD_PROGRAM_ROLE"
        );
    }

    // python: test_add_reward_program_called_by_stranger
    function test_RevertWhen_AddRewardProgramCalledByStranger() external {
        bytes32 addRole = rewardProgramsRegistry.ADD_REWARD_PROGRAM_ROLE();
        assertFalse(
            rewardProgramsRegistry.hasRole(addRole, stranger), "stranger ADD_REWARD_PROGRAM_ROLE"
        );

        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, addRole));
        rewardProgramsRegistry.addRewardProgram(stranger, "");
    }

    // python: test_add_reward_program
    function test_AddsRewardProgram() external {
        vm.expectEmit(address(rewardProgramsRegistry));
        emit RewardProgramAdded(rewardProgram, REWARD_PROGRAM_TITLE);

        vm.recordLogs();

        vm.prank(address(evmScriptExecutorStub));
        rewardProgramsRegistry.addRewardProgram(rewardProgram, REWARD_PROGRAM_TITLE);

        assertEq(vm.getRecordedLogs().length, 1, "events count");

        address[] memory rewardPrograms = rewardProgramsRegistry.getRewardPrograms();
        assertEq(rewardPrograms.length, 1, "rewardPrograms length");
        assertEq(rewardPrograms[0], rewardProgram, "rewardPrograms[0]");

        vm.prank(address(evmScriptExecutorStub));
        vm.expectRevert("REWARD_PROGRAM_ALREADY_ADDED");
        rewardProgramsRegistry.addRewardProgram(rewardProgram, REWARD_PROGRAM_TITLE);
    }

    // python: test_remove_reward_program_called_by_stranger
    function test_RevertWhen_RemoveRewardProgramCalledByStranger() external {
        bytes32 removeRole = rewardProgramsRegistry.REMOVE_REWARD_PROGRAM_ROLE();
        assertFalse(
            rewardProgramsRegistry.hasRole(removeRole, stranger),
            "stranger REMOVE_REWARD_PROGRAM_ROLE"
        );

        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, removeRole));
        rewardProgramsRegistry.removeRewardProgram(stranger);
    }

    // python: test_remove_reward_program_with_not_existed_reward_program
    function test_RevertWhen_RewardProgramToRemoveDoesNotExist() external {
        vm.prank(address(evmScriptExecutorStub));
        vm.expectRevert("REWARD_PROGRAM_NOT_FOUND");
        rewardProgramsRegistry.removeRewardProgram(rewardProgram);
    }

    // python: test_remove_reward_program
    function test_RemovesRewardProgram() external {
        address[] memory rewardPrograms = _givenRewardProgramsAdded(REWARD_PROGRAMS_COUNT);
        uint256[5] memory removingOrder = [uint256(2), 3, 1, 0, 0];

        for (uint256 i; i < removingOrder.length; ++i) {
            address rewardProgramToRemove = rewardPrograms[removingOrder[i]];
            rewardPrograms = _without(rewardPrograms, removingOrder[i]);

            assertTrue(
                rewardProgramsRegistry.isRewardProgram(rewardProgramToRemove),
                "isRewardProgram before"
            );

            vm.expectEmit(address(rewardProgramsRegistry));
            emit RewardProgramRemoved(rewardProgramToRemove);

            vm.recordLogs();

            vm.prank(address(evmScriptExecutorStub));
            rewardProgramsRegistry.removeRewardProgram(rewardProgramToRemove);

            assertEq(vm.getRecordedLogs().length, 1, "events count");
            assertFalse(
                rewardProgramsRegistry.isRewardProgram(rewardProgramToRemove),
                "isRewardProgram after"
            );
            _assertRewardProgramsAre(rewardPrograms);
        }
    }

    function _givenRewardProgramsAdded(uint256 count)
        private
        returns (address[] memory rewardPrograms)
    {
        rewardPrograms = new address[](count);
        for (uint256 i; i < count; ++i) {
            rewardPrograms[i] =
                makeAddr(string(abi.encodePacked("rewardProgram", vm.toString(i + 1))));
        }

        vm.startPrank(address(evmScriptExecutorStub));
        for (uint256 i; i < count; ++i) {
            rewardProgramsRegistry.addRewardProgram(rewardPrograms[i], "");
        }
        vm.stopPrank();
    }

    function _roleHolders() private view returns (address[] memory holders) {
        holders = new address[](2);
        holders[0] = voting;
        holders[1] = address(evmScriptExecutorStub);
    }

    /// @dev `list.pop(index)` of the Python test: `array` without its `index`-th element, order kept
    function _without(address[] memory array, uint256 index)
        private
        pure
        returns (address[] memory rest)
    {
        rest = new address[](array.length - 1);
        for (uint256 i; i < rest.length; ++i) {
            rest[i] = array[i < index ? i : i + 1];
        }
    }

    /// @dev The registry lists exactly `expected`, in any order
    function _assertRewardProgramsAre(address[] memory expected) private view {
        assertEq(
            rewardProgramsRegistry.getRewardPrograms().length,
            expected.length,
            "rewardPrograms length"
        );
        for (uint256 i; i < expected.length; ++i) {
            assertTrue(
                rewardProgramsRegistry.isRewardProgram(expected[i]), "isRewardProgram of remaining"
            );
        }
    }
}
