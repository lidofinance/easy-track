// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {EasyTrack} from "contracts/EasyTrack.sol";
import {EVMScriptExecutor} from "contracts/EVMScriptExecutor.sol";
import {
    IncreaseNodeOperatorStakingLimit
} from "contracts/EVMScriptFactories/IncreaseNodeOperatorStakingLimit.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {Constants} from "test/foundry/unit/helpers/Constants.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {CallsScriptStub} from "test/foundry/unit/stubs/CallsScriptStub.sol";
import {MiniMeTokenStub} from "test/foundry/unit/stubs/MiniMeTokenStub.sol";

contract EVMScriptExecutorTest is Test {
    uint256 internal constant NODE_OPERATOR_ID = 0;

    /// @dev The registry stub's default staking limit
    uint256 internal constant INITIAL_STAKING_LIMIT = 200;
    uint256 internal constant NEW_STAKING_LIMIT = 500;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal voting = makeAddr("voting");
    address internal notContract = makeAddr("notContract");

    MiniMeTokenStub internal ldo;
    CallsScriptStub internal callsScript;
    EasyTrack internal easyTrack;
    EVMScriptExecutor internal evmScriptExecutor;
    NodeOperatorsRegistryStub internal nodeOperatorsRegistryStub;
    IncreaseNodeOperatorStakingLimit internal increaseNodeOperatorStakingLimit;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event ScriptExecuted(address indexed _caller, bytes _evmScript);
    event EasyTrackChanged(address indexed _previousEasyTrack, address indexed _newEasyTrack);

    function setUp() public {
        vm.startPrank(owner);
        ldo = new MiniMeTokenStub();
        callsScript = new CallsScriptStub();
        easyTrack = new EasyTrack(
            address(ldo),
            voting,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );
        evmScriptExecutor = new EVMScriptExecutor(address(callsScript), address(easyTrack));

        nodeOperatorsRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);
        increaseNodeOperatorStakingLimit =
            new IncreaseNodeOperatorStakingLimit(address(nodeOperatorsRegistryStub));
        vm.stopPrank();

        vm.prank(voting);
        easyTrack.setEVMScriptExecutor(address(evmScriptExecutor));
    }

    // python: test_deploy
    function test_Deploy() external {
        vm.prank(owner);
        EVMScriptExecutor newEVMScriptExecutor =
            new EVMScriptExecutor(address(callsScript), address(easyTrack));

        assertEq(newEVMScriptExecutor.callsScript(), address(callsScript), "callsScript");
        assertEq(newEVMScriptExecutor.easyTrack(), address(easyTrack), "easyTrack");
    }

    // python: test_deploy_calls_script_not_contract
    function test_RevertWhen_CallsScriptIsNotContract() external {
        vm.expectRevert("CALLS_SCRIPT_IS_NOT_CONTRACT");
        new EVMScriptExecutor(notContract, address(easyTrack));
    }

    // python: test_deploy_easy_track_not_contract
    function test_RevertWhen_EasyTrackIsNotContract() external {
        vm.expectRevert("EASY_TRACK_IS_NOT_CONTRACT");
        new EVMScriptExecutor(address(callsScript), notContract);
    }

    // python: test_execute_evm_script_revert_msg
    function test_RevertWhen_EVMScriptCallReverts() external {
        // the stub holds 400 signing keys, fewer than the requested limit
        bytes memory evmScript = EVMScripts.encodeCallScript(
            address(increaseNodeOperatorStakingLimit),
            abi.encodeWithSelector(
                IncreaseNodeOperatorStakingLimit.createEVMScript.selector,
                nodeOperator,
                abi.encode(NODE_OPERATOR_ID, NEW_STAKING_LIMIT)
            )
        );

        vm.prank(address(easyTrack));
        vm.expectRevert("NOT_ENOUGH_SIGNING_KEYS");
        evmScriptExecutor.executeEVMScript(evmScript);
    }

    // python: test_execute_evm_script_output
    function test_ExecutesEVMScript() external {
        assertEq(nodeOperatorsRegistryStub.stakingLimit(), INITIAL_STAKING_LIMIT, "stakingLimit");

        bytes memory evmScript = _scriptSettingStakingLimit();

        vm.expectEmit(address(evmScriptExecutor));
        emit ScriptExecuted(address(easyTrack), evmScript);

        vm.prank(address(easyTrack));
        bytes memory output = evmScriptExecutor.executeEVMScript(evmScript);

        assertEq(output, bytes(""), "output");
        assertEq(nodeOperatorsRegistryStub.stakingLimit(), NEW_STAKING_LIMIT, "stakingLimit");
    }

    // python: test_execute_evm_script_caller_validation
    function test_ValidatesEVMScriptCaller() external {
        vm.prank(stranger);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        evmScriptExecutor.executeEVMScript("");

        bytes memory evmScript = _scriptSettingStakingLimit();

        vm.prank(address(easyTrack));
        evmScriptExecutor.executeEVMScript(evmScript);
    }

    // python: test_set_easy_track_called_by_stranger
    function test_RevertWhen_SettingEasyTrackAsStranger() external {
        address newEasyTrack = makeAddr("newEasyTrack");

        vm.prank(stranger);
        vm.expectRevert("Ownable: caller is not the owner");
        evmScriptExecutor.setEasyTrack(newEasyTrack);
    }

    // python: test_set_easy_track_called_by_owner
    function test_SetsEasyTrack() external {
        assertEq(evmScriptExecutor.easyTrack(), address(easyTrack), "easyTrack");

        vm.prank(owner);
        EasyTrack newEasyTrack = new EasyTrack(
            address(ldo),
            voting,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );

        vm.expectEmit(address(evmScriptExecutor));
        emit EasyTrackChanged(address(easyTrack), address(newEasyTrack));

        vm.recordLogs();

        vm.prank(owner);
        evmScriptExecutor.setEasyTrack(address(newEasyTrack));

        assertEq(evmScriptExecutor.easyTrack(), address(newEasyTrack), "easyTrack");
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    /// @dev python: encode_call_script([(stub, stub.setNodeOperatorStakingLimit.encode_input(0, 500))])
    function _scriptSettingStakingLimit() private view returns (bytes memory) {
        return EVMScripts.encodeCallScript(
            address(nodeOperatorsRegistryStub),
            abi.encodeWithSelector(
                NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector,
                NODE_OPERATOR_ID,
                NEW_STAKING_LIMIT
            )
        );
    }
}
