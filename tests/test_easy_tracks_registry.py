import pytest

from brownie import EasyTracksRegistry, accounts, reverts

import constants
import random


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
    "Must update motion duration when value is greater or equal than"
    "MIN_MOTION_DURATION and emits MotionDurationChanged event"
    new_motion_duration = 64 * 60 * 60
    assert easy_tracks_registry.motionDuration(
    ) == constants.DEFAULT_MOTION_DURATION
    tx = easy_tracks_registry.setMotionDuration(new_motion_duration,
                                                {'from': owner})
    assert easy_tracks_registry.motionDuration() == new_motion_duration

    assert len(tx.events) == 1
    assert tx.events[0]['_newDuration'] == new_motion_duration


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
    "Must update objections threshold when value is less or equal"
    "than MAX_OBJECTIONS_THRESHOLD and emits ObjectionsThresholdChanged event"
    new_objections_threshold = 100  # 1%
    assert easy_tracks_registry.objectionsThreshold(
    ) == constants.DEFAULT_OBJECTIONS_THRESHOLD
    tx = easy_tracks_registry.setObjectionsThreshold(new_objections_threshold,
                                                     {'from': owner})
    assert easy_tracks_registry.objectionsThreshold(
    ) == new_objections_threshold

    assert len(tx.events) == 1
    assert tx.events[0]['_newThreshold'] == new_objections_threshold


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
    "and emit ExecutorAdded event"
    executor = accounts[2]
    assert len(easy_tracks_registry.getMotionExecutors()) == 0
    tx = easy_tracks_registry.addMotionExecutor(executor, {'from': owner})
    executors = easy_tracks_registry.getMotionExecutors()
    assert len(executors) == 1
    assert executors[0][0] == 1  # id
    assert executors[0][1] == executor  # executorAddress

    assert len(tx.events) == 1
    assert tx.events[0]['_executorId'] == 1
    assert tx.events[0]['_executorAddress'] == executor


def test_add_motion_executor_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    executor = accounts[2]
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.addMotionExecutor(executor, {'from': stranger})


def test_delete_motion_executor_called_by_owner(owner, easy_tracks_registry):
    "Must delete executor from list of executors and emits ExecutorDeleted event"
    executor = accounts[2]
    easy_tracks_registry.addMotionExecutor(executor, {'from': owner})
    executors = easy_tracks_registry.getMotionExecutors()
    assert len(executors) == 1
    tx = easy_tracks_registry.deleteMotionExecutor(executors[0][0])
    assert len(easy_tracks_registry.getMotionExecutors()) == 0

    assert len(tx.events) == 1
    assert tx.events[0]['_executorId'] == executors[0][0]


def test_delete_motion_executor_with_not_existed_executor_id(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'MOTION_NOT_FOUND'"
    executor = accounts[2]
    easy_tracks_registry.addMotionExecutor(executor, {'from': owner})
    executors = easy_tracks_registry.getMotionExecutors()
    assert len(executors) == 1
    with reverts("MOTION_NOT_FOUND"):
        easy_tracks_registry.deleteMotionExecutor(2)


def test_delete_motion_executor_with_empty_executors(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'MOTION_NOT_FOUND'"
    executors = easy_tracks_registry.getMotionExecutors()
    assert len(executors) == 0
    with reverts("MOTION_NOT_FOUND"):
        easy_tracks_registry.deleteMotionExecutor(0)


def test_delete_motion_executor_with_multiple_executors(
    owner,
    easy_tracks_registry,
):
    executor_addresses = []

    for i in range(0, 5):
        executor_addresses.append((i + 1, accounts[i + 2]))

    for executor in executor_addresses:
        easy_tracks_registry.addMotionExecutor(executor[1], {'from': owner})

    executors = easy_tracks_registry.getMotionExecutors()
    assert len(executors) == len(executor_addresses)

    while len(executor_addresses) > 0:
        index_to_delete = random.randint(0, len(executor_addresses) - 1)
        (id, acc) = executor_addresses.pop(index_to_delete)

        easy_tracks_registry.deleteMotionExecutor(id)
        executors = easy_tracks_registry.getMotionExecutors()

        set1 = set()

        for acc in executor_addresses:
            set1.add((acc[0], acc[1].address))

        assert len(executors) == len(executor_addresses)


def test_delete_motion_executor_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.deleteMotionExecutor(0, {'from': stranger})
