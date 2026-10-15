// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {MotionSettings} from "contracts/MotionSettings.sol";
import {Constants} from "test/foundry/unit/helpers/Constants.sol";
import {TestHelpers} from "test/foundry/unit/helpers/TestHelpers.sol";

contract MotionSettingsTest is Test {
    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    MotionSettings internal motionSettings;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event MotionDurationChanged(uint256 _motionDuration);
    event MotionsCountLimitChanged(uint256 _newMotionsCountLimit);
    event ObjectionsThresholdChanged(uint256 _newThreshold);

    function setUp() public {
        vm.prank(owner);
        motionSettings = new MotionSettings(
            owner,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );
    }

    // python: test_deploy
    function test_Deploy() external {
        vm.prank(owner);
        MotionSettings newMotionSettings = new MotionSettings(
            owner,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );

        assertEq(
            newMotionSettings.MAX_MOTIONS_LIMIT(), Constants.MAX_MOTIONS_LIMIT, "MAX_MOTIONS_LIMIT"
        );
        assertEq(
            newMotionSettings.MAX_OBJECTIONS_THRESHOLD(),
            Constants.MAX_OBJECTIONS_THRESHOLD,
            "MAX_OBJECTIONS_THRESHOLD"
        );
        assertEq(
            newMotionSettings.MIN_MOTION_DURATION(),
            Constants.MIN_MOTION_DURATION,
            "MIN_MOTION_DURATION"
        );
        assertTrue(
            newMotionSettings.hasRole(newMotionSettings.DEFAULT_ADMIN_ROLE(), owner),
            "DEFAULT_ADMIN_ROLE"
        );
        assertEq(
            newMotionSettings.objectionsThreshold(),
            Constants.DEFAULT_OBJECTIONS_THRESHOLD,
            "objectionsThreshold"
        );
        assertEq(
            newMotionSettings.motionsCountLimit(),
            newMotionSettings.MAX_MOTIONS_LIMIT(),
            "motionsCountLimit"
        );
        assertEq(
            newMotionSettings.motionDuration(),
            newMotionSettings.MIN_MOTION_DURATION(),
            "motionDuration"
        );
    }

    // python: test_set_motion_duration_called_with_permissions
    function test_SetsMotionDuration() external {
        uint256 newMotionDuration = 2 * motionSettings.MIN_MOTION_DURATION();

        assertEq(motionSettings.motionDuration(), Constants.MIN_MOTION_DURATION, "motionDuration");

        vm.expectEmit(address(motionSettings));
        emit MotionDurationChanged(newMotionDuration);

        vm.recordLogs();

        vm.prank(owner);
        motionSettings.setMotionDuration(newMotionDuration);

        assertEq(motionSettings.motionDuration(), newMotionDuration, "motionDuration");
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_set_motion_duration_called_without_permissions
    function test_RevertWhen_SettingMotionDurationWithoutAdminRole() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, DEFAULT_ADMIN_ROLE));
        motionSettings.setMotionDuration(0);
    }

    // python: test_set_motion_duration_called_with_too_small_value
    function test_RevertWhen_MotionDurationIsTooSmall() external {
        uint256 motionDuration = motionSettings.MIN_MOTION_DURATION() - 1;

        vm.prank(owner);
        vm.expectRevert("VALUE_TOO_SMALL");
        motionSettings.setMotionDuration(motionDuration);
    }

    // python: test_set_objections_threshold_called_with_permissions
    function test_SetsObjectionsThreshold() external {
        uint256 newObjectionsThreshold = 2 * Constants.DEFAULT_OBJECTIONS_THRESHOLD;

        assertEq(
            motionSettings.objectionsThreshold(),
            Constants.DEFAULT_OBJECTIONS_THRESHOLD,
            "objectionsThreshold"
        );

        vm.expectEmit(address(motionSettings));
        emit ObjectionsThresholdChanged(newObjectionsThreshold);

        vm.recordLogs();

        vm.prank(owner);
        motionSettings.setObjectionsThreshold(newObjectionsThreshold);

        assertEq(
            motionSettings.objectionsThreshold(), newObjectionsThreshold, "objectionsThreshold"
        );
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_set_objections_threshold_without_permissions
    function test_RevertWhen_SettingObjectionsThresholdWithoutAdminRole() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, DEFAULT_ADMIN_ROLE));
        motionSettings.setObjectionsThreshold(0);
    }

    // python: test_set_objections_threshold_called_with_too_large_value
    function test_RevertWhen_ObjectionsThresholdIsTooLarge() external {
        uint256 newObjectionsThreshold = 2 * motionSettings.MAX_OBJECTIONS_THRESHOLD();

        vm.prank(owner);
        vm.expectRevert("VALUE_TOO_LARGE");
        motionSettings.setObjectionsThreshold(newObjectionsThreshold);
    }

    // python: test_set_motions_limit_called_with_permissions
    function test_SetsMotionsCountLimit() external {
        uint256 maxMotionsLimit = motionSettings.MAX_MOTIONS_LIMIT();
        uint256 newMotionsLimit = Constants.MAX_MOTIONS_LIMIT / 2;

        assertEq(motionSettings.motionsCountLimit(), maxMotionsLimit, "motionsCountLimit");

        vm.expectEmit(address(motionSettings));
        emit MotionsCountLimitChanged(newMotionsLimit);

        vm.recordLogs();

        vm.prank(owner);
        motionSettings.setMotionsCountLimit(newMotionsLimit);

        assertEq(motionSettings.motionsCountLimit(), newMotionsLimit, "motionsCountLimit");
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_set_motions_limit_called_without_permissions
    function test_RevertWhen_SettingMotionsCountLimitWithoutAdminRole() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, DEFAULT_ADMIN_ROLE));
        motionSettings.setMotionsCountLimit(0);
    }

    // python: test_set_motions_limit_too_large
    function test_RevertWhen_MotionsCountLimitIsTooLarge() external {
        uint256 newMotionsLimit = 2 * motionSettings.MAX_MOTIONS_LIMIT();

        vm.prank(owner);
        vm.expectRevert("VALUE_TOO_LARGE");
        motionSettings.setMotionsCountLimit(newMotionsLimit);
    }
}
