import random
import pytest

from brownie.network.state import Chain
from brownie import EasyTrackExecutorStub, EasyTracksRegistry, accounts, reverts
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants


def test_deploy_easy_tracks_registry():
    "Must deploy EasyTracksRegistry contract with correct params"
    owner = accounts[0]
    contract = owner.deploy(
        EasyTracksRegistry, constants.ARAGON_AGENT, constants.LDO_TOKEN
    )

    assert contract.motionDuration() == constants.DEFAULT_MOTION_DURATION
    assert contract.objectionsThreshold() == constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert contract.aragonAgent() == constants.ARAGON_AGENT
    assert contract.governanceToken() == constants.LDO_TOKEN


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


def test_set_motions_limit_called_by_owner(owner, easy_tracks_registry):
    "Must set new value for motionsLimit"
    new_motions_limit = 10
    assert easy_tracks_registry.motionsLimit() == 100
    easy_tracks_registry.setMotionsLimit(new_motions_limit)
    assert easy_tracks_registry.motionsLimit() == new_motions_limit


def test_set_motions_limit_called_by_stranger(stranger, easy_tracks_registry):
    "Must fail with error: 'Ownable: caller is not the owner'"
    new_motions_limit = 10
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.setMotionsLimit(new_motions_limit, {"from": stranger})


def test_set_motions_limit_too_large(owner, easy_tracks_registry):
    "Must fail with error: 'VALUE_TOO_LARGE'"
    new_motions_limit = 1000
    with reverts("VALUE_TOO_LARGE"):
        easy_tracks_registry.setMotionsLimit(new_motions_limit, {"from": owner})


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
    assert tx.events["ExecutorAdded"]["_executor"] == easy_track_executor_stub


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


def test_create_motion_without_data(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must create new motion with empty data field"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    easy_tracks_registry.createMotion(
        easy_track_executor_stub, {"from": ldo_holders[0]}
    )
    motions = easy_tracks_registry.getActiveMotions()

    # before create motion guard called
    before_guard_call_data = easy_track_executor_stub.beforeCreateGuardCallData()
    assert before_guard_call_data[0]
    assert before_guard_call_data[1] == ldo_holders[0]
    assert before_guard_call_data[2] == "0x"

    assert len(motions) == 1
    assert motions[0][8] == "0x"


def test_create_motion_with_data(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must create new motion with correct params and emit MotionCreated event"

    chain = Chain()
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    # before create motion guard wasn't called before test
    assert not easy_track_executor_stub.beforeCreateGuardCallData()[0]
    calldata = (
        "0x" + encode_single("(uint256,address)", [256, accounts[0].address]).hex()
    )

    tx = easy_tracks_registry.createMotion(
        easy_track_executor_stub, calldata, {"from": ldo_holders[0]}
    )
    motions = easy_tracks_registry.getActiveMotions()
    assert len(motions) == 1

    # before create motion guard called
    before_guard_call_data = easy_track_executor_stub.beforeCreateGuardCallData()
    assert before_guard_call_data[0]
    assert before_guard_call_data[1] == ldo_holders[0]
    assert before_guard_call_data[2] == calldata

    assert motions[0][0] == 1  # id
    assert motions[0][1] == easy_track_executor_stub  # executor
    assert motions[0][2] == constants.DEFAULT_MOTION_DURATION  # duration
    assert motions[0][3] == chain[-1].timestamp  # startDate
    assert motions[0][4] == chain[-1].number  # snapshotBlock
    assert (
        motions[0][5] == constants.DEFAULT_OBJECTIONS_THRESHOLD
    )  # objectionsThreshold
    assert motions[0][6] == 0  # objectionsAmount
    assert motions[0][7] == 0  # objectionsAmountPct
    assert motions[0][8] == calldata  # data

    assert len(tx.events) == 1
    assert tx.events[0]["_motionId"] == motions[0][0]
    assert tx.events[0]["_executor"] == easy_track_executor_stub
    assert tx.events[0]["data"] == calldata


def test_create_motion_executor_does_not_exist(
    stranger, easy_tracks_registry, easy_track_executor_stub
):
    "Must fail with error: 'EXECUTOR_NOT_FOUND'"
    with reverts("EXECUTOR_NOT_FOUND"):
        easy_tracks_registry.createMotion(easy_track_executor_stub, "")


def test_create_motion_limit_reached(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error: 'MOTIONS_LIMIT_REACHED'"
    easy_tracks_registry.setMotionsLimit(1, {"from": owner})
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    easy_tracks_registry.createMotion(
        easy_track_executor_stub, {"from": ldo_holders[0]}
    )
    with reverts("MOTIONS_LIMIT_REACHED"):
        easy_tracks_registry.createMotion(
            easy_track_executor_stub, {"from": ldo_holders[0]}
        )


def test_cancel_motion_not_found(easy_tracks_registry):
    "Must fail with error: 'MOTION_NOT_FOUND'"
    with reverts("MOTION_NOT_FOUND"):
        easy_tracks_registry.cancelMotion(1)


def test_cancel_motion_without_data(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must remove motion and emit MotionCanceled event"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    easy_tracks_registry.createMotion(easy_track_executor_stub)
    motions = easy_tracks_registry.getActiveMotions()

    assert not easy_track_executor_stub.beforeCancelGuardCallData()[0]
    tx = easy_tracks_registry.cancelMotion(motions[0][0], {"from": ldo_holders[0]})
    assert len(easy_tracks_registry.getActiveMotions()) == 0
    before_cancel_call_data = easy_track_executor_stub.beforeCancelGuardCallData()
    assert before_cancel_call_data[0]
    assert before_cancel_call_data[1] == ldo_holders[0]
    assert before_cancel_call_data[2] == motions[0][0]
    assert before_cancel_call_data[3] == "0x"

    assert len(tx.events) == 1
    assert tx.events["MotionCanceled"]["_motionId"] == motions[0][0]


def test_cancel_motion_with_data(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must remove motion and emit MotionCanceled event"
    "Must remove motion and emit MotionCanceled event"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    easy_tracks_registry.createMotion(easy_track_executor_stub)
    motions = easy_tracks_registry.getActiveMotions()

    assert not easy_track_executor_stub.beforeCancelGuardCallData()[0]
    calldata = "0x" + encode_single("address", owner.address).hex()
    tx = easy_tracks_registry.cancelMotion(
        motions[0][0], calldata, {"from": ldo_holders[0]}
    )
    assert len(easy_tracks_registry.getActiveMotions()) == 0
    before_cancel_call_data = easy_track_executor_stub.beforeCancelGuardCallData()
    assert before_cancel_call_data[0]
    assert before_cancel_call_data[1] == ldo_holders[0]
    assert before_cancel_call_data[2] == motions[0][0]
    assert before_cancel_call_data[3] == calldata

    assert len(tx.events) == 1
    assert tx.events["MotionCanceled"]["_motionId"] == motions[0][0]


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
        easy_tracks_registry.cancelMotion(id_to_delete)

        motions = easy_tracks_registry.getActiveMotions()
        assert len(motions) == len(motion_ids)

        active_motion_ids = []
        for m in motions:
            active_motion_ids.append(m[0])

        len(set(motion_ids).union(active_motion_ids)) == len(motions)


def test_enact_motion_not_exist(owner, easy_tracks_registry, easy_track_executor_stub):
    "Must fail with error: 'MOTION_NOT_FOUND'"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    with reverts("MOTION_NOT_FOUND"):
        easy_tracks_registry.enactMotion(1)


def test_enact_motion_not_passed(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error: 'MOTION_NOT_PASSED'"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    easy_tracks_registry.createMotion(easy_track_executor_stub, "")

    with reverts("MOTION_NOT_PASSED"):
        easy_tracks_registry.enactMotion(1, {"from": ldo_holders[0]})


def test_enact_motion_executor_not_found(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error: 'EXECUTOR_NOT_FOUND'"
    chain = Chain()

    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    easy_tracks_registry.createMotion(easy_track_executor_stub, "")

    easy_tracks_registry.deleteExecutor(easy_track_executor_stub, {"from": owner})

    chain.sleep(constants.DEFAULT_MOTION_DURATION + 1)

    with reverts("EXECUTOR_NOT_FOUND"):
        easy_tracks_registry.enactMotion(1, {"from": ldo_holders[0]})


def test_enact_motion(
    owner,
    aragon_agent_mock,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must pass correct evmScript to aragon agent mock, delete motion and emit MotionEnacted event"
    chain = Chain()

    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    calldata = encode_single(
        "(uint256,address)",
        [2021, accounts[1].address],
    )

    easy_tracks_registry.createMotion(easy_track_executor_stub, calldata)

    motions = easy_tracks_registry.getActiveMotions()

    assert len(motions) == 1

    chain.sleep(constants.DEFAULT_MOTION_DURATION + 1)

    tx = easy_tracks_registry.enactMotion(motions[0][0])

    forward_data = aragon_agent_mock.data()

    assert forward_data == encode_call_script(
        [
            (
                easy_track_executor_stub.address,
                easy_track_executor_stub.execute.encode_input(calldata, ""),
            )
        ]
    )

    assert len(easy_tracks_registry.getActiveMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionEnacted"]["_motionId"] == motions[0][0]


def test_enact_motion_with_data(
    owner,
    aragon_agent_mock,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must pass correct evmScript to aragon agent mock, delete motion and emit MotionEnacted event"
    chain = Chain()

    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    modion_calldata = (
        "0x"
        + encode_single(
            "(uint256,address)",
            [2021, accounts[1].address],
        ).hex()
    )

    easy_tracks_registry.createMotion(easy_track_executor_stub, modion_calldata)

    motions = easy_tracks_registry.getActiveMotions()

    assert len(motions) == 1

    chain.sleep(constants.DEFAULT_MOTION_DURATION + 1)

    enact_calldata = "0x" + encode_single("uint256[]", [1, 2, 3, 4, 5]).hex()

    tx = easy_tracks_registry.enactMotion(motions[0][0], enact_calldata)

    forward_data = aragon_agent_mock.data()

    assert forward_data == encode_call_script(
        [
            (
                easy_track_executor_stub.address,
                easy_track_executor_stub.execute.encode_input(
                    modion_calldata, enact_calldata
                ),
            )
        ]
    )

    assert len(easy_tracks_registry.getActiveMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionEnacted"]["_motionId"] == motions[0][0]


def test_send_objection_motion_not_found(easy_tracks_registry):
    "Must fail with error: 'MOTION_NOT_FOUND'"
    with reverts("MOTION_NOT_FOUND"):
        easy_tracks_registry.sendObjection(1)


def test_send_objection_multiple_times(
    owner,
    ldo_holders,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error: 'ALREADY_OBJECTED'"

    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    easy_tracks_registry.createMotion(easy_track_executor_stub, "")
    easy_tracks_registry.sendObjection(1, {"from": ldo_holders[0]})

    with reverts("ALREADY_OBJECTED"):
        easy_tracks_registry.sendObjection(1, {"from": ldo_holders[0]})


def test_send_objection_passed_motion(
    owner,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error: 'ERROR_MOTION_PASSED'"
    chain = Chain()
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    easy_tracks_registry.createMotion(easy_track_executor_stub, "")
    chain.sleep(constants.DEFAULT_MOTION_DURATION + 1)
    with reverts("MOTION_PASSED"):
        easy_tracks_registry.sendObjection(1)


def test_send_objection_not_ldo_holder(
    owner,
    stranger,
    ldo_token,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must fail with error: 'NOT_ENOUGH_BALANCE'"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})
    easy_tracks_registry.createMotion(easy_track_executor_stub, "")

    assert ldo_token.balanceOf(stranger) == 0

    with reverts("NOT_ENOUGH_BALANCE"):
        easy_tracks_registry.sendObjection(1, {"from": stranger})


def test_send_objection_by_tokens_holder(
    owner,
    ldo_holders,
    ldo_token,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must increase motion objections on correct amount and emit ObjectionSent event"

    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    easy_tracks_registry.createMotion(easy_track_executor_stub, "")

    tx = easy_tracks_registry.sendObjection(1, {"from": ldo_holders[0]})

    motions = easy_tracks_registry.getActiveMotions()

    assert len(motions) == 1

    total_supply = ldo_token.totalSupply()
    holder_balance = ldo_token.balanceOf(ldo_holders[0])
    holder_part = 10000 * holder_balance / total_supply

    assert motions[0][6] == ldo_token.balanceOf(ldo_holders[0])  # objectionsAmount
    assert motions[0][7] == holder_part  # objectionsAmountPct

    assert len(tx.events) == 1

    assert tx.events[0]["_motionId"] == motions[0][0]
    assert tx.events[0]["_voterAddress"] == ldo_holders[0]
    assert tx.events[0]["_weight"] == holder_balance
    assert tx.events[0]["_votingPower"] == total_supply


def test_send_objection_rejected(
    owner,
    ldo_holders,
    ldo_token,
    easy_tracks_registry,
    easy_track_executor_stub,
):
    "Must delete motion and emit MotionRejected event"
    easy_tracks_registry.addExecutor(easy_track_executor_stub, {"from": owner})

    easy_tracks_registry.createMotion(easy_track_executor_stub, "")

    easy_tracks_registry.sendObjection(1, {"from": ldo_holders[0]})  # 0.2 % objections
    easy_tracks_registry.sendObjection(1, {"from": ldo_holders[1]})  # 0.4 % objections

    motions = easy_tracks_registry.getActiveMotions()
    assert len(motions) == 1

    tx = easy_tracks_registry.sendObjection(
        1, {"from": ldo_holders[2]}
    )  # 0.6 % objections

    motions = easy_tracks_registry.getActiveMotions()
    assert len(motions) == 0

    total_supply = ldo_token.totalSupply()
    holder_balance = ldo_token.balanceOf(ldo_holders[2])

    assert len(tx.events) == 2

    assert tx.events[0]["_motionId"] == 1
    assert tx.events[0]["_voterAddress"] == ldo_holders[2]
    assert tx.events[0]["_weight"] == holder_balance
    assert tx.events[0]["_votingPower"] == total_supply

    assert tx.events[1]["_motionId"] == 1
