// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {EasyTrack} from "contracts/EasyTrack.sol";
import {EVMScriptExecutor} from "contracts/EVMScriptExecutor.sol";
import {EVMScriptExecutorStub} from "contracts/test/EVMScriptExecutorStub.sol";
import {EVMScriptFactoryStub} from "contracts/test/EVMScriptFactoryStub.sol";
import {Constants} from "test/foundry/unit/helpers/Constants.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {TestHelpers} from "test/foundry/unit/helpers/TestHelpers.sol";
import {CallsScriptStub} from "test/foundry/unit/stubs/CallsScriptStub.sol";
import {MiniMeTokenStub} from "test/foundry/unit/stubs/MiniMeTokenStub.sol";

contract EasyTrackTest is Test {
    // python: utils/test_helpers.py role constants
    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 internal constant CANCEL_ROLE = keccak256("CANCEL_ROLE");
    bytes32 internal constant PAUSE_ROLE = keccak256("PAUSE_ROLE");
    bytes32 internal constant UNPAUSE_ROLE = keccak256("UNPAUSE_ROLE");

    /// @dev EasyTrack stores 100 % in basis points
    uint256 internal constant HUNDRED_PERCENT = 10000;

    /// @dev The Python reads the live LDO supply from the fork, 1e9 LDO
    uint256 internal constant LDO_TOTAL_SUPPLY = 1_000_000_000 ether;

    /// @dev python: holder_balance_amount, 0.2 % of the supply
    uint256 internal constant HOLDER_BALANCE_AMOUNT = LDO_TOTAL_SUPPLY / 500;

    bytes internal constant EVM_SCRIPT_CALL_DATA = hex"aabbccddeeff";

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");
    address internal agent = makeAddr("agent");
    address[3] internal ldoHolders =
        [makeAddr("ldoHolder1"), makeAddr("ldoHolder2"), makeAddr("ldoHolder3")];

    MiniMeTokenStub internal ldo;
    EasyTrack internal easyTrack;
    EVMScriptExecutor internal evmScriptExecutor;
    EVMScriptFactoryStub internal evmScriptFactoryStub;
    EVMScriptExecutorStub internal evmScriptExecutorStub;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event MotionCreated(
        uint256 indexed _motionId,
        address _creator,
        address indexed _evmScriptFactory,
        bytes _evmScriptCallData,
        bytes _evmScript
    );
    event MotionObjected(
        uint256 indexed _motionId,
        address indexed _objector,
        uint256 _weight,
        uint256 _newObjectionsAmount,
        uint256 _newObjectionsAmountPct
    );
    event MotionRejected(uint256 indexed _motionId);
    event MotionCanceled(uint256 indexed _motionId);
    event MotionEnacted(uint256 indexed _motionId);
    event EVMScriptExecutorChanged(address indexed _evmScriptExecutor);
    event Paused(address account);
    event Unpaused(address account);

    function setUp() public {
        vm.startPrank(owner);
        ldo = new MiniMeTokenStub();
        ldo.mint(agent, LDO_TOTAL_SUPPLY);

        CallsScriptStub callsScript = new CallsScriptStub();
        easyTrack = new EasyTrack(
            address(ldo),
            voting,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );
        evmScriptExecutor = new EVMScriptExecutor(address(callsScript), address(easyTrack));

        evmScriptFactoryStub = new EVMScriptFactoryStub();
        evmScriptExecutorStub = new EVMScriptExecutorStub();
        vm.stopPrank();

        vm.prank(voting);
        easyTrack.setEVMScriptExecutor(address(evmScriptExecutor));
    }

    // python: test_deploy
    function test_Deploy() external {
        vm.prank(owner);
        EasyTrack newEasyTrack = new EasyTrack(
            address(ldo),
            voting,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );

        assertFalse(newEasyTrack.paused(), "paused");
        assertEq(address(newEasyTrack.governanceToken()), address(ldo), "governanceToken");
        assertEq(address(newEasyTrack.evmScriptExecutor()), address(0), "evmScriptExecutor");
        assertTrue(
            newEasyTrack.hasRole(newEasyTrack.DEFAULT_ADMIN_ROLE(), voting), "DEFAULT_ADMIN_ROLE"
        );
        assertTrue(newEasyTrack.hasRole(newEasyTrack.PAUSE_ROLE(), voting), "PAUSE_ROLE");
        assertTrue(newEasyTrack.hasRole(newEasyTrack.UNPAUSE_ROLE(), voting), "UNPAUSE_ROLE");
        assertTrue(newEasyTrack.hasRole(newEasyTrack.CANCEL_ROLE(), voting), "CANCEL_ROLE");
    }

    // python: test_create_motion_when_paused
    function test_RevertWhen_CreatingMotionWhilePaused() external {
        vm.prank(voting);
        easyTrack.pause();

        assertTrue(easyTrack.paused(), "paused");

        vm.prank(stranger);
        vm.expectRevert("Pausable: paused");
        easyTrack.createMotion(address(0), "");
    }

    // python: test_create_motion_evm_script_factory_not_found
    function test_RevertWhen_CreatingMotionWithUnknownFactory() external {
        vm.prank(owner);
        vm.expectRevert("EVM_SCRIPT_FACTORY_NOT_FOUND");
        easyTrack.createMotion(stranger, "");
    }

    // python: test_create_motion_has_no_permissions
    function test_RevertWhen_CreatingMotionWithoutPermissions() external {
        bytes memory wrongPermissions = EVMScripts.createPermission(address(0), 0x11111111);

        vm.prank(voting);
        easyTrack.addEVMScriptFactory(address(evmScriptFactoryStub), wrongPermissions);

        assertNotEq(
            evmScriptFactoryStub.DEFAULT_PERMISSIONS(), wrongPermissions, "DEFAULT_PERMISSIONS"
        );

        vm.prank(stranger);
        vm.expectRevert("HAS_NO_PERMISSIONS");
        easyTrack.createMotion(address(evmScriptFactoryStub), "");
    }

    // python: test_create_motion_motions_limit_reached
    function test_RevertWhen_MotionsLimitIsReached() external {
        vm.prank(voting);
        easyTrack.setMotionsCountLimit(1);

        assertEq(easyTrack.motionsCountLimit(), 1, "motionsCountLimit");

        _registerFactoryStub();

        assertEq(easyTrack.getMotions().length, 0, "motions.length");

        vm.prank(stranger);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        assertEq(easyTrack.getMotions().length, 1, "motions.length");

        vm.prank(stranger);
        vm.expectRevert("MOTIONS_LIMIT_REACHED");
        easyTrack.createMotion(address(evmScriptFactoryStub), "");
    }

    // python: test_create_motion
    function test_CreatesMotion() external {
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        bytes memory defaultEVMScript = evmScriptFactoryStub.DEFAULT_EVM_SCRIPT();

        vm.expectEmit(address(easyTrack));
        emit MotionCreated(
            1, owner, address(evmScriptFactoryStub), EVM_SCRIPT_CALL_DATA, defaultEVMScript
        );

        vm.recordLogs();

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), EVM_SCRIPT_CALL_DATA);

        assertEq(vm.getRecordedLogs().length, 1, "events");

        EasyTrack.Motion[] memory motions = easyTrack.getMotions();
        assertEq(motions.length, 1, "motions.length");

        EasyTrack.Motion memory motion = motions[0];
        assertEq(motion.id, 1, "id");
        assertEq(motion.evmScriptFactory, address(evmScriptFactoryStub), "evmScriptFactory");
        assertEq(motion.creator, owner, "creator");
        assertEq(motion.duration, Constants.MIN_MOTION_DURATION, "duration");
        assertEq(motion.startDate, block.timestamp, "startDate");
        assertEq(motion.snapshotBlock, block.number, "snapshotBlock");
        assertEq(
            motion.objectionsThreshold,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD,
            "objectionsThreshold"
        );
        assertEq(motion.objectionsAmount, 0, "objectionsAmount");
        assertEq(
            motion.evmScriptHash, evmScriptFactoryStub.DEFAULT_EVM_SCRIPT_HASH(), "evmScriptHash"
        );
    }

    // python: test_cancel_motion_not_found
    function test_RevertWhen_CancelingMissingMotion() external {
        vm.prank(owner);
        vm.expectRevert("MOTION_NOT_FOUND");
        easyTrack.cancelMotion(1);
    }

    // python: test_cancel_motion_not_creator
    function test_RevertWhen_CancelingMotionAsNotCreator() external {
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        assertEq(easyTrack.getMotions().length, 1, "motions.length");

        vm.prank(stranger);
        vm.expectRevert("NOT_CREATOR");
        easyTrack.cancelMotion(1);
    }

    // python: test_cancel_motion
    function test_CancelsMotion() external {
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(stranger);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        EasyTrack.Motion[] memory motions = easyTrack.getMotions();
        assertEq(motions.length, 1, "motions.length");

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(motions[0].id);

        vm.recordLogs();

        vm.prank(stranger);
        easyTrack.cancelMotion(motions[0].id);

        assertEq(easyTrack.getMotions().length, 0, "motions.length");
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_cancel_motion_in_random_order
    function test_CancelsMotionsInRandomOrder() external {
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        _createMotions(owner, 3);

        EasyTrack.Motion[] memory motions = easyTrack.getMotions();
        assertEq(motions.length, 3, "motions.length");
        assertEq(motions[0].id, 1, "motions[0].id");
        assertEq(motions[1].id, 2, "motions[1].id");
        assertEq(motions[2].id, 3, "motions[2].id");

        vm.prank(owner);
        easyTrack.cancelMotion(2);

        motions = easyTrack.getMotions();
        assertEq(motions.length, 2, "motions.length");
        assertEq(motions[0].id, 1, "motions[0].id");
        assertEq(motions[1].id, 3, "motions[1].id");

        vm.prank(owner);
        easyTrack.cancelMotion(1);

        motions = easyTrack.getMotions();
        assertEq(motions.length, 1, "motions.length");
        assertEq(motions[0].id, 3, "motions[0].id");

        vm.prank(owner);
        easyTrack.cancelMotion(3);

        assertEq(easyTrack.getMotions().length, 0, "motions.length");
    }

    // python: test_enact_motion_motion_not_found
    function test_RevertWhen_EnactingMissingMotion() external {
        vm.prank(owner);
        vm.expectRevert("MOTION_NOT_FOUND");
        easyTrack.enactMotion(1, "");
    }

    // python: test_enact_motion_when_paused
    function test_RevertWhen_EnactingMotionWhilePaused() external {
        vm.prank(voting);
        easyTrack.pause();

        assertTrue(easyTrack.paused(), "paused");

        vm.prank(stranger);
        vm.expectRevert("Pausable: paused");
        easyTrack.enactMotion(1, "");
    }

    // python: test_enact_motion_when_motion_not_passed
    function test_RevertWhen_EnactingMotionBeforeItPasses() external {
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        EasyTrack.Motion[] memory motions = easyTrack.getMotions();
        assertEq(motions.length, 1, "motions.length");

        vm.prank(owner);
        vm.expectRevert("MOTION_NOT_PASSED");
        easyTrack.enactMotion(motions[0].id, "");
    }

    // python: test_enact_motion_unexpected_evm_script
    function test_RevertWhen_EnactingMotionWithUnexpectedEVMScript() external {
        _allowFactoryStubToSetEVMScript();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        EasyTrack.Motion[] memory motions = easyTrack.getMotions();
        assertEq(motions.length, 1, "motions.length");

        vm.warp(block.timestamp + Constants.MIN_MOTION_DURATION + 1);

        // changes the script, so its hash no longer matches the motion's
        evmScriptFactoryStub.setEVMScript(_scriptCallingSetEVMScript(hex"001122"));

        vm.prank(owner);
        vm.expectRevert("UNEXPECTED_EVM_SCRIPT");
        easyTrack.enactMotion(motions[0].id, "");
    }

    // python: test_enact_motion
    function test_EnactsMotion() external {
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(voting);
        easyTrack.setEVMScriptExecutor(address(evmScriptExecutorStub));

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        EasyTrack.Motion[] memory motions = easyTrack.getMotions();
        assertEq(motions.length, 1, "motions.length");

        vm.warp(block.timestamp + Constants.MIN_MOTION_DURATION + 1);

        assertEq(evmScriptExecutorStub.evmScript(), bytes(""), "evmScript");

        vm.expectEmit(address(easyTrack));
        emit MotionEnacted(motions[0].id);

        vm.recordLogs();

        vm.prank(owner);
        easyTrack.enactMotion(motions[0].id, "");

        assertEq(easyTrack.getMotions().length, 0, "motions.length");
        assertEq(vm.getRecordedLogs().length, 1, "events");
        assertEq(
            evmScriptExecutorStub.evmScript(),
            evmScriptFactoryStub.DEFAULT_EVM_SCRIPT(),
            "evmScript"
        );
    }

    // python: test_object_to_motion_motion_not_found
    function test_RevertWhen_ObjectingToMissingMotion() external {
        vm.prank(owner);
        vm.expectRevert("MOTION_NOT_FOUND");
        easyTrack.objectToMotion(1);
    }

    // python: test_object_to_motion_multiple_times
    function test_RevertWhen_ObjectingTwice() external {
        _distributeHolderBalances();
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        vm.prank(ldoHolders[0]);
        easyTrack.objectToMotion(1);

        assertTrue(easyTrack.objections(1, ldoHolders[0]), "objections");

        vm.prank(ldoHolders[0]);
        vm.expectRevert("ALREADY_OBJECTED");
        easyTrack.objectToMotion(1);
    }

    // python: test_object_to_motion_not_ldo_holder
    function test_RevertWhen_ObjectorHoldsNoLDO() external {
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        assertEq(ldo.balanceOf(stranger), 0, "balanceOf");

        vm.prank(stranger);
        vm.expectRevert("NOT_ENOUGH_BALANCE");
        easyTrack.objectToMotion(1);
    }

    // python: test_object_to_motion_by_tokens_holder
    function test_ObjectsToMotionAsTokenHolder() external {
        _distributeHolderBalances();
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        uint256 holderBalance = ldo.balanceOf(ldoHolders[0]);
        uint256 objectionsAmountPct = (HUNDRED_PERCENT * holderBalance) / ldo.totalSupply();

        vm.expectEmit(address(easyTrack));
        emit MotionObjected(1, ldoHolders[0], holderBalance, holderBalance, objectionsAmountPct);

        vm.recordLogs();

        vm.prank(ldoHolders[0]);
        easyTrack.objectToMotion(1);

        EasyTrack.Motion memory motion = easyTrack.getMotions()[0];
        assertEq(motion.objectionsAmount, holderBalance, "objectionsAmount");
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_object_to_motion_rejected
    function test_RejectsMotionWhenObjectionsReachThreshold() external {
        _distributeHolderBalances();
        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        // 0.2 % objections
        vm.prank(ldoHolders[0]);
        easyTrack.objectToMotion(1);

        // 0.4 % objections
        vm.prank(ldoHolders[1]);
        easyTrack.objectToMotion(1);

        assertEq(easyTrack.getMotions().length, 1, "motions.length");

        uint256 weight = ldo.balanceOf(ldoHolders[2]);
        uint256 objectionsAmount =
            ldo.balanceOf(ldoHolders[0]) + ldo.balanceOf(ldoHolders[1]) + weight;
        uint256 objectionsAmountPct = (HUNDRED_PERCENT * objectionsAmount) / ldo.totalSupply();

        // 0.6 % objections cross the 0.5 % threshold
        vm.expectEmit(address(easyTrack));
        emit MotionObjected(1, ldoHolders[2], weight, objectionsAmount, objectionsAmountPct);

        vm.expectEmit(address(easyTrack));
        emit MotionRejected(1);

        vm.recordLogs();

        vm.prank(ldoHolders[2]);
        easyTrack.objectToMotion(1);

        assertEq(easyTrack.getMotions().length, 0, "motions.length");
        assertEq(vm.getRecordedLogs().length, 2, "events");
    }

    // python: test_object_to_motion_edge_case
    function test_ObjectionsThresholdEdgeCase() external {
        uint256 objectionsThresholdAmount =
            (easyTrack.objectionsThreshold() * ldo.totalSupply()) / HUNDRED_PERCENT - 1;

        vm.startPrank(agent);
        ldo.transfer(owner, objectionsThresholdAmount);
        ldo.transfer(stranger, 1);
        vm.stopPrank();

        _registerFactoryStub();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        // one wei short of the threshold
        vm.prank(owner);
        easyTrack.objectToMotion(1);

        assertEq(easyTrack.getMotions().length, 1, "motions.length");

        // exactly the threshold
        vm.prank(stranger);
        easyTrack.objectToMotion(1);

        assertEq(easyTrack.getMotions().length, 0, "motions.length");
    }

    // python: test_cancel_motions_called_without_permissions
    function test_RevertWhen_CancelingMotionsWithoutCancelRole() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, CANCEL_ROLE));
        easyTrack.cancelMotions(new uint256[](0));
    }

    // python: test_cancel_motions
    function test_CancelsMotions() external {
        _registerFactoryStub();
        _createMotions(owner, 5);

        for (uint256 motionId = 1; motionId <= 5; ++motionId) {
            assertEq(easyTrack.getMotion(motionId).id, motionId, "getMotion");
        }

        // ids 6 and 7 do not exist and are skipped silently
        uint256[] memory motionIdsToCancel = new uint256[](5);
        motionIdsToCancel[0] = 6;
        motionIdsToCancel[1] = 7;
        motionIdsToCancel[2] = 1;
        motionIdsToCancel[3] = 3;
        motionIdsToCancel[4] = 5;

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(1);

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(3);

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(5);

        vm.recordLogs();

        vm.prank(voting);
        easyTrack.cancelMotions(motionIdsToCancel);

        EasyTrack.Motion[] memory motions = easyTrack.getMotions();
        assertEq(motions.length, 2, "motions.length");
        assertEq(motions[0].id, 4, "motions[0].id");
        assertEq(motions[1].id, 2, "motions[1].id");
        assertEq(vm.getRecordedLogs().length, 3, "events");
    }

    // python: test_cancel_all_motions_called_by_stranger
    function test_RevertWhen_CancelingAllMotionsAsStranger() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, CANCEL_ROLE));
        easyTrack.cancelAllMotions();
    }

    // python: test_cancel_all_motions
    function test_CancelsAllMotions() external {
        _registerFactoryStub();
        _createMotions(owner, 5);

        for (uint256 motionId = 1; motionId <= 5; ++motionId) {
            assertEq(easyTrack.getMotion(motionId).id, motionId, "getMotion");
        }

        // canceled from the last motion to the first
        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(5);

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(4);

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(3);

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(2);

        vm.expectEmit(address(easyTrack));
        emit MotionCanceled(1);

        vm.recordLogs();

        vm.prank(voting);
        easyTrack.cancelAllMotions();

        assertEq(vm.getRecordedLogs().length, 5, "events");
    }

    // python: test_set_evm_script_executor_called_by_stranger
    function test_RevertWhen_SettingEVMScriptExecutorAsStranger() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, DEFAULT_ADMIN_ROLE));
        easyTrack.setEVMScriptExecutor(address(0));
    }

    // python: test_set_evm_script_executor_called_by_owner
    function test_SetsEVMScriptExecutor() external {
        assertEq(
            address(easyTrack.evmScriptExecutor()), address(evmScriptExecutor), "evmScriptExecutor"
        );

        vm.expectEmit(address(easyTrack));
        emit EVMScriptExecutorChanged(address(evmScriptExecutorStub));

        vm.prank(voting);
        easyTrack.setEVMScriptExecutor(address(evmScriptExecutorStub));

        assertEq(
            address(easyTrack.evmScriptExecutor()),
            address(evmScriptExecutorStub),
            "evmScriptExecutor"
        );
    }

    // python: test_pause_called_without_permissions
    function test_RevertWhen_PausingWithoutPauseRole() external {
        assertFalse(easyTrack.paused(), "paused");

        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, PAUSE_ROLE));
        easyTrack.pause();

        assertFalse(easyTrack.paused(), "paused");
    }

    // python: test_pause_called_with_permissions
    function test_Pauses() external {
        assertFalse(easyTrack.paused(), "paused");

        vm.expectEmit(address(easyTrack));
        emit Paused(voting);

        vm.recordLogs();

        vm.prank(voting);
        easyTrack.pause();

        assertTrue(easyTrack.paused(), "paused");
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_pause_called_when_paused
    function test_RevertWhen_PausingWhilePaused() external {
        assertFalse(easyTrack.paused(), "paused");

        vm.prank(voting);
        easyTrack.pause();

        assertTrue(easyTrack.paused(), "paused");

        vm.prank(voting);
        vm.expectRevert("Pausable: paused");
        easyTrack.pause();
    }

    // python: test_unpause_called_without_permissions
    function test_RevertWhen_UnpausingWithoutUnpauseRole() external {
        vm.prank(voting);
        easyTrack.pause();

        assertTrue(easyTrack.paused(), "paused");

        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, UNPAUSE_ROLE));
        easyTrack.unpause();

        assertTrue(easyTrack.paused(), "paused");
    }

    // python: test_unpause_called_when_not_paused
    function test_RevertWhen_UnpausingWhileNotPaused() external {
        assertFalse(easyTrack.paused(), "paused");

        vm.prank(voting);
        vm.expectRevert("Pausable: not paused");
        easyTrack.unpause();
    }

    // python: test_unpause_called_with_permissions
    function test_Unpauses() external {
        vm.prank(voting);
        easyTrack.pause();

        assertTrue(easyTrack.paused(), "paused");

        vm.expectEmit(address(easyTrack));
        emit Unpaused(voting);

        vm.recordLogs();

        vm.prank(voting);
        easyTrack.unpause();

        assertFalse(easyTrack.paused(), "paused");
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_can_object_to_motion
    function test_CanObjectToMotion() external {
        _distributeHolderBalances();
        _allowFactoryStubToSetEVMScript();

        assertTrue(
            easyTrack.isEVMScriptFactory(address(evmScriptFactoryStub)), "isEVMScriptFactory"
        );

        vm.prank(owner);
        easyTrack.createMotion(address(evmScriptFactoryStub), "");

        assertFalse(easyTrack.canObjectToMotion(1, stranger), "canObjectToMotion(stranger)");
        assertTrue(easyTrack.canObjectToMotion(1, ldoHolders[0]), "canObjectToMotion(holder)");

        vm.prank(ldoHolders[0]);
        easyTrack.objectToMotion(1);

        assertFalse(
            easyTrack.canObjectToMotion(1, ldoHolders[0]),
            "canObjectToMotion(holder) after objecting"
        );
    }

    /// @dev python: distribute_holder_balance. Each holder gets 0.2 % of the supply from the agent
    function _distributeHolderBalances() private {
        vm.startPrank(agent);
        for (uint256 i; i < ldoHolders.length; ++i) {
            ldo.transfer(ldoHolders[i], HOLDER_BALANCE_AMOUNT);
        }

        vm.stopPrank();
    }

    /// @dev Registers the factory stub with its default permissions
    function _registerFactoryStub() private {
        bytes memory permissions = evmScriptFactoryStub.DEFAULT_PERMISSIONS();

        vm.prank(voting);
        easyTrack.addEVMScriptFactory(address(evmScriptFactoryStub), permissions);
    }

    /// @dev Registers the factory stub with a permission for its own `setEVMScript` and makes it
    /// return a script calling that method, so the stub can rewrite its script mid-motion
    function _allowFactoryStubToSetEVMScript() private {
        bytes memory permissions = EVMScripts.createPermission(
            address(evmScriptFactoryStub), EVMScriptFactoryStub.setEVMScript.selector
        );

        vm.prank(voting);
        easyTrack.addEVMScriptFactory(address(evmScriptFactoryStub), permissions);

        evmScriptFactoryStub.setEVMScript(_scriptCallingSetEVMScript(""));
    }

    function _createMotions(address creator, uint256 count) private {
        vm.startPrank(creator);
        for (uint256 i; i < count; ++i) {
            easyTrack.createMotion(address(evmScriptFactoryStub), "");
        }

        vm.stopPrank();
    }

    /// @dev python: encode_call_script([(stub, stub.setEVMScript.encode_input(evmScript))])
    function _scriptCallingSetEVMScript(bytes memory evmScript)
        private
        view
        returns (bytes memory)
    {
        return EVMScripts.encodeCallScript(
            address(evmScriptFactoryStub),
            abi.encodeWithSelector(EVMScriptFactoryStub.setEVMScript.selector, evmScript)
        );
    }
}
