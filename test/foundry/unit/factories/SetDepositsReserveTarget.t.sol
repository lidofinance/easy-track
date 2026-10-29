// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {SetDepositsReserveTarget} from "contracts/EVMScriptFactories/SetDepositsReserveTarget.sol";
import {ILido} from "contracts/interfaces/ILido.sol";
import {LidoStub} from "contracts/test/LidoStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract SetDepositsReserveTargetTest is Test {
    uint256 internal constant INITIAL_DEPOSITS_RESERVE_TARGET = 1500 ether;
    uint256 internal constant MAX_DEPOSITS_RESERVE_TARGET = 3000 ether;
    uint256 internal constant NEW_DEPOSITS_RESERVE_TARGET = 2000 ether;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    LidoStub internal lidoStub;
    SetDepositsReserveTarget internal setDepositsReserveTarget;

    function setUp() public {
        lidoStub = new LidoStub(INITIAL_DEPOSITS_RESERVE_TARGET);

        vm.prank(owner);
        setDepositsReserveTarget =
            new SetDepositsReserveTarget(owner, MAX_DEPOSITS_RESERVE_TARGET, address(lidoStub));

        vm.label(address(lidoStub), "lidoStub");
        vm.label(address(setDepositsReserveTarget), "setDepositsReserveTarget");
    }

    function test_SetsInitialState() external view {
        assertEq(setDepositsReserveTarget.trustedCaller(), owner, "trustedCaller");
        assertEq(
            setDepositsReserveTarget.MAX_DEPOSITS_RESERVE_TARGET(),
            MAX_DEPOSITS_RESERVE_TARGET,
            "MAX_DEPOSITS_RESERVE_TARGET"
        );
        assertEq(address(setDepositsReserveTarget.lido()), address(lidoStub), "lido");
    }

    function test_CreatesEVMScript() external view {
        bytes memory evmScript = setDepositsReserveTarget.createEVMScript(
            owner, abi.encode(NEW_DEPOSITS_RESERVE_TARGET)
        );

        assertEq(
            evmScript, _setDepositsReserveTargetScript(NEW_DEPOSITS_RESERVE_TARGET), "evmScript"
        );
    }

    function test_AcceptsMaxDepositsReserveTarget() external view {
        bytes memory evmScript = setDepositsReserveTarget.createEVMScript(
            owner, abi.encode(MAX_DEPOSITS_RESERVE_TARGET)
        );

        assertEq(
            evmScript, _setDepositsReserveTargetScript(MAX_DEPOSITS_RESERVE_TARGET), "evmScript"
        );
    }

    function test_AcceptsZeroDepositsReserveTarget() external view {
        bytes memory evmScript =
            setDepositsReserveTarget.createEVMScript(owner, abi.encode(uint256(0)));

        assertEq(evmScript, _setDepositsReserveTargetScript(0), "evmScript");
    }

    function test_RevertWhen_DepositsReserveTargetIsTooHigh() external {
        vm.expectRevert("DEPOSITS_RESERVE_TARGET_TOO_HIGH");
        setDepositsReserveTarget.createEVMScript(owner, abi.encode(MAX_DEPOSITS_RESERVE_TARGET + 1));
    }

    function test_RevertWhen_DepositsReserveTargetIsUnchanged() external {
        vm.expectRevert("SAME_DEPOSITS_RESERVE_TARGET");
        setDepositsReserveTarget.createEVMScript(owner, abi.encode(INITIAL_DEPOSITS_RESERVE_TARGET));
    }

    function test_RevertWhen_CreatorIsNotTrusted() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        setDepositsReserveTarget.createEVMScript(stranger, abi.encode(NEW_DEPOSITS_RESERVE_TARGET));
    }

    function test_RevertWhen_CallDataIsMalformed() external {
        vm.expectRevert(bytes(""));
        setDepositsReserveTarget.createEVMScript(owner, hex"00");
    }

    function test_DecodesEVMScriptCallData() external view {
        uint256 decoded = setDepositsReserveTarget.decodeEVMScriptCallData(
            abi.encode(NEW_DEPOSITS_RESERVE_TARGET)
        );

        assertEq(decoded, NEW_DEPOSITS_RESERVE_TARGET, "newDepositsReserveTarget");
    }

    function _setDepositsReserveTargetScript(uint256 target) private view returns (bytes memory) {
        return EVMScripts.encodeCallScript(
            address(lidoStub),
            abi.encodeWithSelector(ILido.setDepositsReserveTarget.selector, target)
        );
    }
}
