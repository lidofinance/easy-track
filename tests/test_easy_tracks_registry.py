import pytest

from brownie import EasyTracksRegistry, accounts, reverts

import constants


def test_deploy_easy_tracks_registry():
    "Must deploy EasyTracksRegistry contract with correct params"
    owner = accounts[0]
    contract = owner.deploy(EasyTracksRegistry, constants.ARAGON_AGENT)

    assert contract.motionDuration() == constants.DEFAULT_MOTION_DURATION
    assert contract.objectionsThreshold(
    ) == constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert contract.aragonAgent() == constants.ARAGON_AGENT


def test_set_motion_duration_called_by_owner(
    owner,
    easy_tracks_registry,
):
    "Must update motion duration when value is greater or equal than MIN_MOTION_DURATION"
    new_motion_duration = 64 * 60 * 60
    assert easy_tracks_registry.motionDuration(
    ) == constants.DEFAULT_MOTION_DURATION
    easy_tracks_registry.setMotionDuration(new_motion_duration,
                                           {'from': owner})
    assert easy_tracks_registry.motionDuration() == new_motion_duration


def test_set_motion_duration_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_motion_duration = 64 * 60 * 60
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.setMotionDuration(new_motion_duration,
                                               {'from': stranger})


def test_set_motion_duration_called_with_too_small_value(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'VALUE_TOO_SMALL'"
    new_motion_duration = 32 * 60 * 60
    with reverts("VALUE_TOO_SMALL"):
        easy_tracks_registry.setMotionDuration(new_motion_duration,
                                               {'from': owner})


def test_set_objections_threshold_called_by_owner(
    owner,
    easy_tracks_registry,
):
    "Must update objections threshold when value is less or equal than MAX_OBJECTIONS_THRESHOLD"
    new_objections_threshold = 100  # 1%
    assert easy_tracks_registry.objectionsThreshold(
    ) == constants.DEFAULT_OBJECTIONS_THRESHOLD
    easy_tracks_registry.setObjectionsThreshold(new_objections_threshold,
                                                {'from': owner})
    assert easy_tracks_registry.objectionsThreshold(
    ) == new_objections_threshold


def test_set_objections_threshold_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_objections_threshold = 100  # 1%
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.setObjectionsThreshold(new_objections_threshold,
                                                    {'from': stranger})


def test_set_objections_threshold_called_with_too_large_value(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'VALUE_TOO_LARGE'"
    new_objections_threshold = 600  # 6%
    with reverts("VALUE_TOO_LARGE"):
        easy_tracks_registry.setObjectionsThreshold(new_objections_threshold,
                                                    {'from': owner})


def test_add_motion_executor_called_by_owner(
    owner,
    easy_tracks_registry,
):
    "Must add new executor with passed address to allowed executors list"
    executor = accounts[2]
    assert len(easy_tracks_registry.getMotionExecutors()) == 0
    easy_tracks_registry.addMotionExecutor(executor, {'from': owner})
    executors = easy_tracks_registry.getMotionExecutors()
    assert len(executors) == 1
    assert executors[0][0] == 1  # id
    assert executors[0][1] == executor  # executorAddress


def test_add_motion_executor_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    executor = accounts[2]
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.addMotionExecutor(executor, {'from': stranger})
