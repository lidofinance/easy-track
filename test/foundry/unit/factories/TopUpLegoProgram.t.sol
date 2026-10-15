// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {TopUpLegoProgram} from "contracts/EVMScriptFactories/TopUpLegoProgram.sol";
import {IFinance} from "contracts/interfaces/IFinance.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract TopUpLegoProgramTest is Test {
    /// @dev The mainnet reward tokens the Python test pays out, used as plain addresses
    address internal constant LDO = 0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32;
    address internal constant STETH = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84;
    uint256 internal constant LDO_REWARD_AMOUNT = 1 ether;
    uint256 internal constant STETH_REWARD_AMOUNT = 2 ether;
    string internal constant PAYMENT_REFERENCE = "Lego Program Transfer";

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal legoProgram = makeAddr("legoProgram");
    address internal finance = makeAddr("finance");

    TopUpLegoProgram internal topUpLegoProgram;

    function setUp() public {
        vm.prank(owner);
        topUpLegoProgram = new TopUpLegoProgram(owner, IFinance(finance), legoProgram);

        vm.label(address(topUpLegoProgram), "topUpLegoProgram");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(topUpLegoProgram.trustedCaller(), owner, "trustedCaller");
        assertEq(address(topUpLegoProgram.finance()), finance, "finance");
        assertEq(topUpLegoProgram.legoProgram(), legoProgram, "legoProgram");
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.prank(stranger);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        topUpLegoProgram.createEVMScript(
            stranger, _encodeCallData(new address[](0), new uint256[](0))
        );
    }

    // python: test_create_evm_script_data_length_mismatch
    function test_RevertWhen_DataLengthMismatch() external {
        vm.expectRevert("LENGTH_MISMATCH");
        topUpLegoProgram.createEVMScript(owner, _encodeCallData(_rewardTokens(), _amounts(1)));
    }

    // python: test_create_evm_script_empty_data
    function test_RevertWhen_DataIsEmpty() external {
        vm.expectRevert("EMPTY_DATA");
        topUpLegoProgram.createEVMScript(owner, _encodeCallData(new address[](0), new uint256[](0)));
    }

    // python: test_create_evm_script_zero_amount
    function test_RevertWhen_AmountIsZero() external {
        vm.expectRevert("ZERO_AMOUNT");
        topUpLegoProgram.createEVMScript(owner, _encodeCallData(_rewardTokens(), _amounts(1, 0)));
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = topUpLegoProgram.createEVMScript(
            owner, _encodeCallData(_rewardTokens(), _rewardAmounts())
        );

        address[] memory targets = new address[](2);
        targets[0] = finance;
        targets[1] = finance;

        bytes[] memory payments = new bytes[](2);
        payments[0] = _encodeNewImmediatePayment(LDO, LDO_REWARD_AMOUNT);
        payments[1] = _encodeNewImmediatePayment(STETH, STETH_REWARD_AMOUNT);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, payments), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        (address[] memory rewardTokens, uint256[] memory amounts) = topUpLegoProgram.decodeEVMScriptCallData(
            _encodeCallData(_rewardTokens(), _rewardAmounts())
        );

        assertEq(rewardTokens, _rewardTokens(), "rewardTokens");
        assertEq(amounts, _rewardAmounts(), "amounts");
    }

    function _rewardTokens() private pure returns (address[] memory rewardTokens) {
        rewardTokens = new address[](2);
        rewardTokens[0] = LDO;
        rewardTokens[1] = STETH;
    }

    function _rewardAmounts() private pure returns (uint256[] memory) {
        return _amounts(LDO_REWARD_AMOUNT, STETH_REWARD_AMOUNT);
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

    function _encodeCallData(address[] memory rewardTokens, uint256[] memory amounts)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(rewardTokens, amounts);
    }

    function _encodeNewImmediatePayment(address token, uint256 amount)
        private
        view
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            IFinance.newImmediatePayment.selector, token, legoProgram, amount, PAYMENT_REFERENCE
        );
    }
}
