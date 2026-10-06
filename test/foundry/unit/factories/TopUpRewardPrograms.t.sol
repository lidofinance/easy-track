// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {TopUpRewardPrograms} from "contracts/EVMScriptFactories/TopUpRewardPrograms.sol";
import {RewardProgramsRegistry} from "contracts/RewardProgramsRegistry.sol";
import {IFinance} from "contracts/interfaces/IFinance.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract TopUpRewardProgramsTest is Test {
    address internal constant FIRST_REWARD_PROGRAM = 0xffffFfFffffFfffffFFfFfFFfFffFfFfFFFfFfaA;
    address internal constant SECOND_REWARD_PROGRAM = 0xfFFFfFfFfffFffFfFfFFfFFfffFfFfFffffffFbb;
    uint256 internal constant FIRST_REWARD_PROGRAM_AMOUNT = 1 ether;
    uint256 internal constant SECOND_REWARD_PROGRAM_AMOUNT = 2 ether;
    uint256 internal constant NOT_ALLOWED_REWARD_PROGRAM_AMOUNT = 3 ether;
    string internal constant PAYMENT_REFERENCE = "Reward program top up";

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");
    address internal finance = makeAddr("finance");
    address internal ldo = makeAddr("ldo");
    address internal notAllowedRewardProgram = makeAddr("notAllowedRewardProgram");

    EVMScriptExecutorStub internal evmScriptExecutorStub;
    RewardProgramsRegistry internal rewardProgramsRegistry;
    TopUpRewardPrograms internal topUpRewardPrograms;

    function setUp() public {
        vm.startPrank(owner);
        evmScriptExecutorStub = new EVMScriptExecutorStub();
        rewardProgramsRegistry = new RewardProgramsRegistry(voting, _roleHolders(), _roleHolders());
        topUpRewardPrograms =
            new TopUpRewardPrograms(owner, address(rewardProgramsRegistry), finance, ldo);
        vm.stopPrank();

        vm.label(address(evmScriptExecutorStub), "evmScriptExecutorStub");
        vm.label(address(rewardProgramsRegistry), "rewardProgramsRegistry");
        vm.label(address(topUpRewardPrograms), "topUpRewardPrograms");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(topUpRewardPrograms.trustedCaller(), owner, "trustedCaller");
        assertEq(address(topUpRewardPrograms.finance()), finance, "finance");
        assertEq(topUpRewardPrograms.rewardToken(), ldo, "rewardToken");
        assertEq(
            address(topUpRewardPrograms.rewardProgramsRegistry()),
            address(rewardProgramsRegistry),
            "rewardProgramsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.prank(stranger);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        topUpRewardPrograms.createEVMScript(
            stranger, _encodeCallData(new address[](0), new uint256[](0))
        );
    }

    // python: test_create_evm_script_data_length_mismatch
    function test_RevertWhen_DataLengthMismatch() external {
        vm.expectRevert("LENGTH_MISMATCH");
        topUpRewardPrograms.createEVMScript(owner, _encodeCallData(_rewardPrograms(), _amounts(1)));
    }

    // python: test_create_evm_script_empty_data
    function test_RevertWhen_DataIsEmpty() external {
        vm.expectRevert("EMPTY_DATA");
        topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(new address[](0), new uint256[](0))
        );
    }

    // python: test_create_evm_script_zero_amount
    function test_RevertWhen_AmountIsZero() external {
        _givenRewardProgramsAdded();

        vm.expectRevert("ZERO_AMOUNT");
        topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(_rewardPrograms(), _amounts(1, 0))
        );
    }

    // python: test_create_evm_script_reward_program_not_allowed
    function test_RevertWhen_RewardProgramNotAllowed() external {
        vm.expectRevert("REWARD_PROGRAM_NOT_ALLOWED");
        topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(_rewardPrograms(), _rewardProgramAmounts())
        );

        _givenRewardProgramsAdded();

        address[] memory rewardPrograms = new address[](3);
        rewardPrograms[0] = FIRST_REWARD_PROGRAM;
        rewardPrograms[1] = SECOND_REWARD_PROGRAM;
        rewardPrograms[2] = notAllowedRewardProgram;

        uint256[] memory amounts = new uint256[](3);
        amounts[0] = FIRST_REWARD_PROGRAM_AMOUNT;
        amounts[1] = SECOND_REWARD_PROGRAM_AMOUNT;
        amounts[2] = NOT_ALLOWED_REWARD_PROGRAM_AMOUNT;

        vm.expectRevert("REWARD_PROGRAM_NOT_ALLOWED");
        topUpRewardPrograms.createEVMScript(owner, _encodeCallData(rewardPrograms, amounts));
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        _givenRewardProgramsAdded();

        bytes memory evmScript = topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(_rewardPrograms(), _rewardProgramAmounts())
        );

        address[] memory targets = new address[](2);
        targets[0] = finance;
        targets[1] = finance;

        bytes[] memory payments = new bytes[](2);
        payments[0] = _encodeNewImmediatePayment(FIRST_REWARD_PROGRAM, FIRST_REWARD_PROGRAM_AMOUNT);
        payments[1] =
            _encodeNewImmediatePayment(SECOND_REWARD_PROGRAM, SECOND_REWARD_PROGRAM_AMOUNT);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, payments), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        (address[] memory rewardPrograms, uint256[] memory amounts) = topUpRewardPrograms.decodeEVMScriptCallData(
            _encodeCallData(_rewardPrograms(), _rewardProgramAmounts())
        );

        assertEq(rewardPrograms, _rewardPrograms(), "rewardPrograms");
        assertEq(amounts, _rewardProgramAmounts(), "amounts");
    }

    function _givenRewardProgramsAdded() private {
        vm.startPrank(address(evmScriptExecutorStub));
        rewardProgramsRegistry.addRewardProgram(FIRST_REWARD_PROGRAM, "");
        rewardProgramsRegistry.addRewardProgram(SECOND_REWARD_PROGRAM, "");
        vm.stopPrank();
    }

    function _roleHolders() private view returns (address[] memory holders) {
        holders = new address[](2);
        holders[0] = voting;
        holders[1] = address(evmScriptExecutorStub);
    }

    function _rewardPrograms() private pure returns (address[] memory rewardPrograms) {
        rewardPrograms = new address[](2);
        rewardPrograms[0] = FIRST_REWARD_PROGRAM;
        rewardPrograms[1] = SECOND_REWARD_PROGRAM;
    }

    function _rewardProgramAmounts() private pure returns (uint256[] memory) {
        return _amounts(FIRST_REWARD_PROGRAM_AMOUNT, SECOND_REWARD_PROGRAM_AMOUNT);
    }

    function _amounts(uint256 amount) private pure returns (uint256[] memory amounts) {
        amounts = new uint256[](1);
        amounts[0] = amount;
    }

    function _amounts(uint256 first, uint256 second)
        private
        pure
        returns (uint256[] memory amounts)
    {
        amounts = new uint256[](2);
        amounts[0] = first;
        amounts[1] = second;
    }

    function _encodeCallData(address[] memory rewardPrograms, uint256[] memory amounts)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(rewardPrograms, amounts);
    }

    function _encodeNewImmediatePayment(address rewardProgram, uint256 amount)
        private
        view
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            IFinance.newImmediatePayment.selector, ldo, rewardProgram, amount, PAYMENT_REFERENCE
        );
    }
}
