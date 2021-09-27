import constants
from brownie import MotionSettings, reverts
from utils.test_helpers import access_controll_revert_message


def test_deploy(owner):
    "Must deploy MotionsRegistry contract with correct params"
    contract = owner.deploy(
        MotionSettings,
        owner,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )

    # constants
    assert contract.MAX_MOTIONS_LIMIT() == constants.MAX_MOTIONS_LIMIT
    assert contract.MAX_OBJECTIONS_THRESHOLD() == constants.MAX_OBJECTIONS_THRESHOLD
    assert contract.MIN_MOTION_DURATION() == constants.MIN_MOTION_DURATION

    # roles
    assert contract.hasRole(contract.DEFAULT_ADMIN_ROLE(), owner)

    # variables
    assert contract.objectionsThreshold() == constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert contract.motionsCountLimit() == contract.MAX_MOTIONS_LIMIT()
    assert contract.motionDuration() == contract.MIN_MOTION_DURATION()


def test_set_motion_duration_called_with_permissions(owner, motion_settings):
    "Must update motion duration if value is greater or equal than"
    "MIN_MOTION_DURATION and emits MotionDurationChanged(_motionDuration) event"
    min_motion_duration = motion_settings.MIN_MOTION_DURATION()
    new_motion_duration = 2 * min_motion_duration
    assert motion_settings.motionDuration() == min_motion_duration
    tx = motion_settings.setMotionDuration(new_motion_duration, {"from": owner})
    assert motion_settings.motionDuration() == new_motion_duration

    assert len(tx.events) == 1
    assert tx.events["MotionDurationChanged"]["_motionDuration"] == new_motion_duration


def test_set_motion_duration_called_without_permissions(stranger, motion_settings):
    "Must revert with correct Access Control message"
    "if called by address without 'DEFAULT_ADMIN_ROLE'"
    with reverts(access_controll_revert_message(stranger)):
        motion_settings.setMotionDuration(0, {"from": stranger})


def test_set_motion_duration_called_with_too_small_value(owner, motion_settings):
    "Must revert with 'VALUE_TOO_SMALL' message"
    motion_duration = motion_settings.MIN_MOTION_DURATION() - 1
    with reverts("VALUE_TOO_SMALL"):
        motion_settings.setMotionDuration(motion_duration, {"from": owner})


def test_set_objections_threshold_called_with_permissions(owner, motion_settings):
    "Must update objections threshold when value is less or equal"
    "than MAX_OBJECTIONS_THRESHOLD and emits ObjectionsThresholdChanged(_newThreshold) event"
    new_objections_threshold = 2 * constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert (
        motion_settings.objectionsThreshold() == constants.DEFAULT_OBJECTIONS_THRESHOLD
    )
    tx = motion_settings.setObjectionsThreshold(
        new_objections_threshold, {"from": owner}
    )
    assert motion_settings.objectionsThreshold() == new_objections_threshold

    assert len(tx.events) == 1
    assert (
        tx.events["ObjectionsThresholdChanged"]["_newThreshold"]
        == new_objections_threshold
    )


def test_set_objections_threshold_without_permissions(stranger, motion_settings):
    "Must revert with correct Access Control message"
    "if called by address without 'DEFAULT_ADMIN_ROLE'"
    with reverts(access_controll_revert_message(stranger)):
        motion_settings.setObjectionsThreshold(0, {"from": stranger})


def test_set_objections_threshold_called_with_too_large_value(owner, motion_settings):
    "Must revert with message 'VALUE_TOO_LARGE' when new"
    "threshold is greater than MAX_OBJECTIONS_THRESHOLD"
    new_objections_threshold = 2 * motion_settings.MAX_OBJECTIONS_THRESHOLD()
    with reverts("VALUE_TOO_LARGE"):
        motion_settings.setObjectionsThreshold(
            new_objections_threshold, {"from": owner}
        )


def test_set_motions_limit_called_with_permissions(owner, motion_settings):
    "Must set new value for motionsCountLimit and emit"
    "MotionsCountLimitChanged(_newMotionsCountLimit) event"
    max_motions_limit = motion_settings.MAX_MOTIONS_LIMIT()
    new_motions_limit = int(motion_settings.MAX_MOTIONS_LIMIT() / 2)

    assert motion_settings.motionsCountLimit() == max_motions_limit
    tx = motion_settings.setMotionsCountLimit(new_motions_limit, {"from": owner})
    assert motion_settings.motionsCountLimit() == new_motions_limit

    assert len(tx.events) == 1
    assert (
        tx.events["MotionsCountLimitChanged"]["_newMotionsCountLimit"]
        == new_motions_limit
    )


def test_set_motions_limit_called_without_permissions(stranger, motion_settings):
    "Must revert with correct Access Control message"
    "if called by address without 'DEFAULT_ADMIN_ROLE'"
    with reverts(access_controll_revert_message(stranger)):
        motion_settings.setMotionsCountLimit(0, {"from": stranger})


def test_set_motions_limit_too_large(owner, motion_settings):
    "Must revert with message: 'VALUE_TOO_LARGE' when new value greater than MAX_MOTIONS_LIMIT"
    new_motions_limit = 2 * motion_settings.MAX_MOTIONS_LIMIT()
    with reverts("VALUE_TOO_LARGE"):
        motion_settings.setMotionsCountLimit(new_motions_limit, {"from": owner})
