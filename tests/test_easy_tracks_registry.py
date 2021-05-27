import random
import pytest

from brownie.network.state import Chain
from brownie import EasyTrackExecutorStub, EasyTracksRegistry, accounts, reverts
from eth_abi import encode_single

import constants


def test_deploy_easy_tracks_registry():
    "Must deploy EasyTracksRegistry contract with correct params"
    owner = accounts[0]
    contract = owner.deploy(EasyTracksRegistry, constants.ARAGON_AGENT)

    assert contract.motionDuration() == constants.DEFAULT_MOTION_DURATION
    assert contract.objectionsThreshold() == constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert contract.aragonAgent() == constants.ARAGON_AGENT


def test_set_motion_duration_called_by_owner(
    owner,
    easy_tracks_registry,
):
    "Must update motion duration when value is greater or equal than"
    "MIN_MOTION_DURATION and emits MotionDurationChanged event"
    new_motion_duration = 64 * 60 * 60
    assert easy_tracks_registry.motionDuration() == constants.DEFAULT_MOTION_DURATION
    tx = easy_tracks_registry.setMotionDuration(new_motion_duration, {"from": owner})
    assert easy_tracks_registry.motionDuration() == new_motion_duration

    assert len(tx.events) == 1
    assert tx.events[0]["_newDuration"] == new_motion_duration


def test_set_motion_duration_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_motion_duration = 64 * 60 * 60
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.setMotionDuration(new_motion_duration, {"from": stranger})


def test_set_motion_duration_called_with_too_small_value(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'VALUE_TOO_SMALL'"
    new_motion_duration = 32 * 60 * 60
    with reverts("VALUE_TOO_SMALL"):
        easy_tracks_registry.setMotionDuration(new_motion_duration, {"from": owner})


def test_set_objections_threshold_called_by_owner(
    owner,
    easy_tracks_registry,
):
    "Must update objections threshold when value is less or equal"
    "than MAX_OBJECTIONS_THRESHOLD and emits ObjectionsThresholdChanged event"
    new_objections_threshold = 100  # 1%
    assert (
        easy_tracks_registry.objectionsThreshold()
        == constants.DEFAULT_OBJECTIONS_THRESHOLD
    )
    tx = easy_tracks_registry.setObjectionsThreshold(
        new_objections_threshold, {"from": owner}
    )
    assert easy_tracks_registry.objectionsThreshold() == new_objections_threshold

    assert len(tx.events) == 1
    assert tx.events[0]["_newThreshold"] == new_objections_threshold


def test_set_objections_threshold_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_objections_threshold = 100  # 1%
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.setObjectionsThreshold(
            new_objections_threshold, {"from": stranger}
        )


def test_set_objections_threshold_called_with_too_large_value(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'VALUE_TOO_LARGE'"
    new_objections_threshold = 600  # 6%
    with reverts("VALUE_TOO_LARGE"):
        easy_tracks_registry.setObjectionsThreshold(
            new_objections_threshold, {"from": owner}
        )


def test_add_executor_called_by_owner(
    owner,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must add new executor with passed address to allowed executors list"
    "and emit ExecutorAdded event"
    assert len(easy_tracks_registry.getExecutors()) == 0
    tx = easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    executors = easy_tracks_registry.getExecutors()
    assert len(executors) == 1
    assert executors[0] == easy_track_executor_stub

    assert len(tx.events) == 1
    assert tx.events[0]["_executor"] == easy_track_executor_stub
    assert (
        tx.events[0]["_executeMethodId"] == easy_track_executor_stub.executeMethodId()
    )
    assert (
        tx.events[0]["_executeCalldataSignature"]
        == easy_track_executor_stub.executeCalldataSignature()
    )
    assert tx.events[0]["_description"] == easy_track_executor_stub.description()


def test_add_executor_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    executor = accounts[2]
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.addExecutor(executor, {"from": stranger})


def test_add_executor_duplicate(
    owner,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error 'EXECUTOR_ALREADY_ADDED'"
    assert len(easy_tracks_registry.getExecutors()) == 0
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    executors = easy_tracks_registry.getExecutors()
    assert len(executors) == 1
    assert executors[0] == easy_track_executor_stub

    with reverts("EXECUTOR_ALREADY_ADDED"):
        easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})


def test_delete_executor_called_by_owner(
    owner,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must delete executor from list of executors and emits ExecutorDeleted event"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    executors = easy_tracks_registry.getExecutors()
    assert len(executors) == 1
    tx = easy_tracks_registry.deleteExecutor(executors[0])
    assert len(easy_tracks_registry.getExecutors()) == 0

    assert len(tx.events) == 1
    assert tx.events[0]["_executor"] == executors[0]


def test_delete_executor_not_exist(
    owner,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error 'EXECUTOR_NOT_FOUND'"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    executors = easy_tracks_registry.getExecutors()
    assert len(executors) == 1
    with reverts("EXECUTOR_NOT_FOUND"):
        easy_tracks_registry.deleteExecutor(accounts[1])


def test_delete_executor_with_empty_executors(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'EXECUTOR_NOT_FOUND'"
    executors = easy_tracks_registry.getExecutors()
    assert len(executors) == 0
    with reverts("EXECUTOR_NOT_FOUND"):
        easy_tracks_registry.deleteExecutor(accounts[1])


def test_delete_executor_with_multiple_executors(
    owner,
    easy_tracks_registry,
):
    executor_addresses = []

    # deploy executors
    for i in range(0, 5):
        ex = accounts[1].deploy(EasyTrackExecutorStub, easy_tracks_registry)
        executor_addresses.append(ex.address)

    # add executors
    for executor in executor_addresses:
        easy_tracks_registry.addExecutor(executor, {"from": owner})

    executors = easy_tracks_registry.getExecutors()
    assert len(executors) == len(executor_addresses)

    while len(executor_addresses) > 0:
        index_to_delete = random.randint(0, len(executor_addresses) - 1)
        executor = executor_addresses.pop(index_to_delete)

        easy_tracks_registry.deleteExecutor(executor)
        executors = easy_tracks_registry.getExecutors()

        assert len(executors) == len(executor_addresses)

        # validate that was deleted correct address by join
        # test set with resulting set their size must be same
        assert len(set(executors).union(executor_addresses)) == len(executors)


def test_delete_motion_executor_called_by_stranger(
    stranger, easy_tracks_registry, easy_track_executor_stub
):
    "Must fail with error 'Ownable: caller is not the owner'"
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.deleteExecutor(
            easy_track_executor_stub, {"from": stranger}
        )


def test_create_motion(owner, easy_tracks_registry, easy_track_executor_stub):
    "Must create new motion with correct params and emit MotionCreated event"

    chain = Chain()
    assert len(easy_tracks_registry.getExecutors()) == 0
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    assert len(easy_tracks_registry.getExecutors()) == 1

    calldata = encode_single(
        easy_track_executor_stub.executeCalldataSignature(),
        [2021, accounts[1].address],
    )
    # before create motion guard wasn't called before test
    assert not easy_track_executor_stub.isBeforeCreateGuardCalled()

    tx = easy_tracks_registry.createMotion(easy_track_executor_stub, calldata)
    motions = easy_tracks_registry.getActiveMotions()

    assert len(motions) == 1

    # before create motion guard called
    assert easy_track_executor_stub.isBeforeCreateGuardCalled()

    assert motions[0][0] == 1  # id
    assert motions[0][1] == easy_track_executor_stub  # executor
    assert motions[0][2] == constants.DEFAULT_MOTION_DURATION  # duration
    assert motions[0][3] == chain[-1].timestamp  # startDate
    assert motions[0][4] == chain[-1].number  # snapshotBlock
    assert (
        motions[0][5] == constants.DEFAULT_OBJECTIONS_THRESHOLD
    )  # objectionsThreshold
    assert motions[0][6] == 0  # objectionsAmount
    assert motions[0][7] == "0x" + calldata.hex()  # data

    assert len(tx.events) == 1
    assert tx.events[0]["_motionId"] == motions[0][0]
    assert tx.events[0]["_executor"] == easy_track_executor_stub
    assert tx.events[0]["data"] == "0x" + calldata.hex()


def test_create_motion_executor_does_not_exist(
    stranger, easy_tracks_registry, easy_track_executor_stub
):
    "Must fail with error: 'EXECUTOR_NOT_FOUND'"
    with reverts("EXECUTOR_NOT_FOUND"):
        easy_tracks_registry.createMotion(easy_track_executor_stub, "")


def test_cancel_motion_not_found(easy_tracks_registry):
    "Must fail with error: 'MOTION_NOT_FOUND'"
    with reverts("MOTION_NOT_FOUND"):
        easy_tracks_registry.cancelMotion(1, "")


def test_cancel_motion(owner, easy_tracks_registry, easy_track_executor_stub):
    "Must remove motion and emit MotionCanceled event"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    easy_tracks_registry.createMotion(easy_track_executor_stub, "")
    motions = easy_tracks_registry.getActiveMotions()

    assert not easy_track_executor_stub.isBeforeCancelGuardCalled()
    tx = easy_tracks_registry.cancelMotion(motions[0][0], "")
    assert len(easy_tracks_registry.getActiveMotions()) == 0
    assert easy_track_executor_stub.isBeforeCancelGuardCalled()

    assert len(tx.events) == 1
    assert tx.events[0]["_motionId"] == motions[0][0]


def test_cancel_motion_many_times(
    owner, easy_tracks_registry, easy_track_executor_stub
):
    "Must remove motions in correct order"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    motion_ids = []
    for i in range(0, 5):
        tx = easy_tracks_registry.createMotion(easy_track_executor_stub, "")
        motion_ids.append(tx.events[0]["_motionId"])

    while len(motion_ids) > 0:
        index = random.randint(0, len(motion_ids) - 1)
        id_to_delete = motion_ids.pop(index)
        easy_tracks_registry.cancelMotion(id_to_delete, "")

        motions = easy_tracks_registry.getActiveMotions()
        assert len(motions) == len(motion_ids)

        active_motion_ids = []
        for m in motions:
            active_motion_ids.append(m[0])

        len(set(motion_ids).union(active_motion_ids)) == len(motions)