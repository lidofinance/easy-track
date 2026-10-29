// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {TopUpRewardPrograms} from "contracts/EVMScriptFactories/TopUpRewardPrograms.sol";
import {RewardProgramsRegistry} from "contracts/RewardProgramsRegistry.sol";
import {IFinance} from "contracts/interfaces/IFinance.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
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
        address[] memory roleHolders = Arrays.list(voting, address(evmScriptExecutorStub));
        rewardProgramsRegistry = new RewardProgramsRegistry(voting, roleHolders, roleHolders);
        topUpRewardPrograms =
            new TopUpRewardPrograms(owner, address(rewardProgramsRegistry), finance, ldo);
        vm.stopPrank();

        vm.label(address(evmScriptExecutorStub), "evmScriptExecutorStub");
        vm.label(address(rewardProgramsRegistry), "rewardProgramsRegistry");
        vm.label(address(topUpRewardPrograms), "topUpRewardPrograms");
    }

    function test_SetsInitialState() external view {
        assertEq(topUpRewardPrograms.trustedCaller(), owner, "trustedCaller");
        assertEq(address(topUpRewardPrograms.finance()), finance, "finance");
        assertEq(topUpRewardPrograms.rewardToken(), ldo, "rewardToken");
        assertEq(
            address(topUpRewardPrograms.rewardProgramsRegistry()),
            address(rewardProgramsRegistry),
            "rewardProgramsRegistry"
        );
    }

    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.prank(stranger);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        topUpRewardPrograms.createEVMScript(
            stranger, _encodeCallData(new address[](0), new uint256[](0))
        );
    }

    function test_RevertWhen_DataLengthMismatch() external {
        vm.expectRevert("LENGTH_MISMATCH");
        topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(_rewardPrograms(), Arrays.list(1))
        );
    }

    function test_RevertWhen_DataIsEmpty() external {
        vm.expectRevert("EMPTY_DATA");
        topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(new address[](0), new uint256[](0))
        );
    }

    function test_RevertWhen_AmountIsZero() external {
        _addRewardPrograms();

        vm.expectRevert("ZERO_AMOUNT");
        topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(_rewardPrograms(), Arrays.list(1, 0))
        );
    }

    function test_RevertWhen_RewardProgramNotAllowed() external {
        vm.expectRevert("REWARD_PROGRAM_NOT_ALLOWED");
        topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(_rewardPrograms(), _rewardProgramAmounts())
        );

        _addRewardPrograms();

        address[] memory rewardPrograms =
            Arrays.list(FIRST_REWARD_PROGRAM, SECOND_REWARD_PROGRAM, notAllowedRewardProgram);

        uint256[] memory amounts = Arrays.list(
            FIRST_REWARD_PROGRAM_AMOUNT,
            SECOND_REWARD_PROGRAM_AMOUNT,
            NOT_ALLOWED_REWARD_PROGRAM_AMOUNT
        );

        vm.expectRevert("REWARD_PROGRAM_NOT_ALLOWED");
        topUpRewardPrograms.createEVMScript(owner, _encodeCallData(rewardPrograms, amounts));
    }

    function test_CreatesEVMScript() external {
        _addRewardPrograms();

        bytes memory evmScript = topUpRewardPrograms.createEVMScript(
            owner, _encodeCallData(_rewardPrograms(), _rewardProgramAmounts())
        );

        address[] memory targets = Arrays.list(finance, finance);

        bytes[] memory payments = Arrays.list(
            _encodeNewImmediatePayment(FIRST_REWARD_PROGRAM, FIRST_REWARD_PROGRAM_AMOUNT),
            _encodeNewImmediatePayment(SECOND_REWARD_PROGRAM, SECOND_REWARD_PROGRAM_AMOUNT)
        );

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, payments), "evmScript");
    }

    function test_DecodesEVMScriptCallData() external view {
        (address[] memory rewardPrograms, uint256[] memory amounts) = topUpRewardPrograms.decodeEVMScriptCallData(
            _encodeCallData(_rewardPrograms(), _rewardProgramAmounts())
        );

        assertEq(rewardPrograms, _rewardPrograms(), "rewardPrograms");
        assertEq(amounts, _rewardProgramAmounts(), "amounts");
    }

    function _addRewardPrograms() private {
        vm.startPrank(address(evmScriptExecutorStub));
        rewardProgramsRegistry.addRewardProgram(FIRST_REWARD_PROGRAM, "");
        rewardProgramsRegistry.addRewardProgram(SECOND_REWARD_PROGRAM, "");
        vm.stopPrank();
    }

    function _rewardPrograms() private pure returns (address[] memory) {
        return Arrays.list(FIRST_REWARD_PROGRAM, SECOND_REWARD_PROGRAM);
    }

    function _rewardProgramAmounts() private pure returns (uint256[] memory) {
        return Arrays.list(FIRST_REWARD_PROGRAM_AMOUNT, SECOND_REWARD_PROGRAM_AMOUNT);
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
