import random
import pytest

from brownie.network.state import Chain
from brownie import MotionsRegistry, accounts, reverts
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants

MOTION_CALLDATA_STUB = "0xdddddddddddddddddddddddddddddddd"


def test_deploy(owner, easy_tracks_registry, ldo_token, agent):
    "Must deploy MotionsRegistry contract with correct params"
    contract = owner.deploy(MotionsRegistry, easy_tracks_registry, ldo_token, agent)

    # constants
    assert contract.MAX_MOTIONS_LIMIT() == 100
    assert contract.MAX_OBJECTIONS_THRESHOLD() == 500
    assert contract.MIN_MOTION_DURATION() == 48 * 60 * 60

    # variables
    assert contract.owner() == owner
    assert contract.aragonAgent() == agent
    assert contract.governanceToken() == ldo_token
    assert contract.objectionsThreshold() == constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert contract.motionsCountLimit() == contract.MAX_MOTIONS_LIMIT()
    assert contract.motionDuration() == contract.MIN_MOTION_DURATION()


def test_set_motion_duration_called_by_owner(owner, motions_registry):
    "Must update motion duration when value is greater or equal than"
    "MIN_MOTION_DURATION and emits MotionDurationChanged event"
    min_motion_duration = motions_registry.MIN_MOTION_DURATION()
    new_motion_duration = 2 * min_motion_duration
    assert motions_registry.motionDuration() == min_motion_duration
    tx = motions_registry.setMotionDuration(new_motion_duration, {"from": owner})
    assert motions_registry.motionDuration() == new_motion_duration

    assert len(tx.events) == 1
    assert tx.events["MotionDurationChanged"]["_motionDuration"] == new_motion_duration


def test_set_motion_duration_called_by_stranger(stranger, motions_registry):
    "Must fail with error 'Ownable: caller is not the owner'"
    with reverts("Ownable: caller is not the owner"):
        motions_registry.setMotionDuration(0, {"from": stranger})


def test_set_motion_duration_called_with_too_small_value(owner, motions_registry):
    "Must fail with error 'VALUE_TOO_SMALL' when new duration is less than MIN_MOTION_DURATION"
    motion_duration = motions_registry.MIN_MOTION_DURATION() - 1
    with reverts("VALUE_TOO_SMALL"):
        motions_registry.setMotionDuration(motion_duration, {"from": owner})


def test_set_objections_threshold_called_by_owner(owner, motions_registry):
    "Must update objections threshold when value is less or equal"
    "than MAX_OBJECTIONS_THRESHOLD and emits ObjectionsThresholdChanged event"
    new_objections_threshold = 2 * constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert (
        motions_registry.objectionsThreshold() == constants.DEFAULT_OBJECTIONS_THRESHOLD
    )
    tx = motions_registry.setObjectionsThreshold(
        new_objections_threshold, {"from": owner}
    )
    assert motions_registry.objectionsThreshold() == new_objections_threshold

    assert len(tx.events) == 1
    assert (
        tx.events["ObjectionsThresholdChanged"]["_newThreshold"]
        == new_objections_threshold
    )


def test_set_objections_threshold_called_by_stranger(stranger, motions_registry):
    "Must fail with error 'Ownable: caller is not the owner'"
    with reverts("Ownable: caller is not the owner"):
        motions_registry.setObjectionsThreshold(0, {"from": stranger})


def test_set_objections_threshold_called_with_too_large_value(owner, motions_registry):
    "Must fail with error 'VALUE_TOO_LARGE' when new"
    "threshold is greater than MAX_OBJECTIONS_THRESHOLD"
    new_objections_threshold = 2 * motions_registry.MAX_OBJECTIONS_THRESHOLD()
    with reverts("VALUE_TOO_LARGE"):
        motions_registry.setObjectionsThreshold(
            new_objections_threshold, {"from": owner}
        )


def test_set_motions_limit_called_by_owner(motions_registry):
    "Must set new value for motionsCountLimit and emit MotionsCountLimitChanged event"
    max_motions_limit = motions_registry.MAX_MOTIONS_LIMIT()
    new_motions_limit = int(motions_registry.MAX_MOTIONS_LIMIT() / 2)

    assert motions_registry.motionsCountLimit() == max_motions_limit
    tx = motions_registry.setMotionsCountLimit(new_motions_limit)
    assert motions_registry.motionsCountLimit() == new_motions_limit

    assert len(tx.events) == 1
    assert (
        tx.events["MotionsCountLimitChanged"]["_newMotionsCountLimit"]
        == new_motions_limit
    )


def test_set_motions_limit_called_by_stranger(stranger, motions_registry):
    "Must fail with error: 'Ownable: caller is not the owner'"
    with reverts("Ownable: caller is not the owner"):
        motions_registry.setMotionsCountLimit(0, {"from": stranger})


def test_set_motions_limit_too_large(owner, motions_registry):
    "Must fail with error: 'VALUE_TOO_LARGE'"
    new_motions_limit = 2 * motions_registry.MAX_MOTIONS_LIMIT()
    with reverts("VALUE_TOO_LARGE"):
        motions_registry.setMotionsCountLimit(new_motions_limit, {"from": owner})


def test_create_motion_called_not_by_easy_track(stranger, motions_registry):
    "Must fail with error 'NOT_EASY_TRACK'"
    with reverts("NOT_EASY_TRACK"):
        motions_registry.createMotion("0x", {"from": stranger})


def test_create_motion_motions_limit_exceeded(
    owner, motions_registry, easy_tracks_registry
):
    "Must fail with error 'MOTIONS_LIMIT_REACHED'"
    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # decrease motions count limit for test purposes
    motions_limit = 3
    motions_registry.setMotionsCountLimit(motions_limit, {"from": owner})
    assert motions_registry.motionsCountLimit() == motions_limit

    # reach limit of motions
    for i in range(motions_limit):
        motions_registry.createMotion("0x", {"from": easy_track})

    with reverts("MOTIONS_LIMIT_REACHED"):
        motions_registry.createMotion("0x", {"from": easy_track})


def test_create_motion(owner, motions_registry, easy_tracks_registry):
    "Must create new motion with correct data and emit"
    "MotionCreated event when called by easy track"

    chain = Chain()

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    assert len(motions_registry.getMotions()) == 0
    tx = motions_registry.createMotion(MOTION_CALLDATA_STUB, {"from": easy_track})

    assert tx.events["MotionCreated"]["_motionId"] == 1
    assert tx.events["MotionCreated"]["_easyTrack"] == easy_track
    assert tx.events["MotionCreated"]["_data"] == MOTION_CALLDATA_STUB

    motions = motions_registry.getMotions()
    assert len(motions) == 1

    assert motions[0][0] == 1  # id
    assert motions[0][1] == easy_track  # easyTrack
    assert motions[0][2] == constants.DEFAULT_MOTION_DURATION  # duration
    assert motions[0][3] == chain[-1].timestamp  # startDate
    assert motions[0][4] == chain[-1].number  # snapshotBlock
    assert (
        motions[0][5] == constants.DEFAULT_OBJECTIONS_THRESHOLD
    )  # objectionsThreshold
    assert motions[0][6] == 0  # objectionsAmount
    assert motions[0][7] == 0  # objectionsAmountPct
    assert motions[0][8] == MOTION_CALLDATA_STUB  # data


def test_cancel_motion_called_not_by_easy_track(stranger, motions_registry):
    "Must fail with error 'NOT_EASY_TRACK'"
    with reverts("NOT_EASY_TRACK"):
        motions_registry.createMotion("0x", {"from": stranger})


def test_cancel_motion_not_found(owner, motions_registry, easy_tracks_registry):
    "Must fail with error: 'MOTION_NOT_FOUND'"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    assert len(motions_registry.getMotions()) == 0

    with reverts("MOTION_NOT_FOUND"):
        motions_registry.cancelMotion(1, {"from": easy_track})


def test_cancel_motion(owner, motions_registry, easy_tracks_registry):
    "Must remove motion and emit MotionCanceled event"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # add motion
    assert len(motions_registry.getMotions()) == 0
    motions_registry.createMotion("0x", {"from": easy_track})
    motions = motions_registry.getMotions()
    assert len(motions) == 1
    assert motions[0][0] == 1  # id

    tx = motions_registry.cancelMotion(1, {"from": easy_track})

    assert len(motions_registry.getMotions()) == 0
    assert tx.events["MotionCanceled"]["_motionId"] == motions[0][0]


def test_cancel_motion_easy_track_mismatch(
    owner, motions_registry, easy_tracks_registry
):
    "Must fail with error 'WRONG_EASYTRACK' when try"
    "cancel motion created by different easy track"

    # add pair of easy tracks to create motions
    easy_tracks = accounts[2:4]
    for easy_track in easy_tracks:
        assert not easy_tracks_registry.isEasyTrack(easy_track)
        easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
        assert easy_tracks_registry.isEasyTrack(easy_track)

    motion_creator = easy_tracks[0]
    motion_canceler = easy_tracks[1]

    # add motion
    assert len(motions_registry.getMotions()) == 0
    motions_registry.createMotion("0x", {"from": motion_creator})
    motions = motions_registry.getMotions()
    assert len(motions) == 1
    assert motions[0][0] == 1  # id
    assert motions[0][1] == motion_creator  # easyTrack

    with reverts("WRONG_EASYTRACK"):
        motions_registry.cancelMotion(1, {"from": motion_canceler})


def test_cancel_motion_many_times(owner, motions_registry, easy_tracks_registry):
    "Must remove motions in correct order"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    motion_ids = []
    for i in range(0, 5):
        tx = motions_registry.createMotion("", {"from": easy_track})
        motion_ids.append(tx.events[0]["_motionId"])

    while len(motion_ids) > 0:
        index = random.randint(0, len(motion_ids) - 1)
        id_to_delete = motion_ids.pop(index)
        motions_registry.cancelMotion(id_to_delete, {"from": easy_track})

        motions = motions_registry.getMotions()
        assert len(motions) == len(motion_ids)

        active_motion_ids = []
        for motion in motions:
            active_motion_ids.append(motion[0])

        len(set(motion_ids).union(active_motion_ids)) == len(motions)


def test_enact_motion_called_not_by_easy_track(stranger, motions_registry):
    "Must fail with error 'NOT_EASY_TRACK'"
    with reverts("NOT_EASY_TRACK"):
        motions_registry.enactMotion(1, {"from": stranger})


def test_enact_motion_not_exist(owner, motions_registry, easy_tracks_registry):
    "Must fail with error: 'MOTION_NOT_FOUND'"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    with reverts("MOTION_NOT_FOUND"):
        motions_registry.enactMotion(1, {"from": easy_track})


def test_enact_motion_easy_tracks_mismatch(
    owner, easy_tracks_registry, motions_registry
):
    "Must fail with error 'WRONG_EASYTRACK' when try"
    "enact motion created by different easy track"

    # add pair of easy tracks to create motions
    chain = Chain()
    easy_tracks = accounts[2:4]
    for easy_track in easy_tracks:
        assert not easy_tracks_registry.isEasyTrack(easy_track)
        easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
        assert easy_tracks_registry.isEasyTrack(easy_track)

    motion_creator = easy_tracks[0]
    motion_canceler = easy_tracks[1]

    # add motion
    assert len(motions_registry.getMotions()) == 0
    motions_registry.createMotion("0x", {"from": motion_creator})
    motions = motions_registry.getMotions()
    assert len(motions) == 1
    assert motions[0][0] == 1  # id
    assert motions[0][1] == motion_creator  # easyTrack

    # wait motion becomes passed
    motion_duration = motions_registry.motionDuration()
    chain.sleep(motion_duration + 1)

    with reverts("WRONG_EASYTRACK"):
        motions_registry.enactMotion(1, {"from": motion_canceler})


def test_enact_motion_not_passed(
    owner, stranger, ldo_holders, easy_tracks_registry, motions_registry
):
    "Must fail with error: 'MOTION_NOT_PASSED'"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    motions_registry.createMotion("0x", {"from": easy_track})

    with reverts("MOTION_NOT_PASSED"):
        motions_registry.enactMotion(1, {"from": easy_track})


def test_enact_motion_without_evm_script(
    owner, easy_tracks_registry, motions_registry, aragon_agent_mock
):
    "Must delete motion, emit MotionEnacted"
    "event and doesn't forward script to Aragon agent"

    chain = Chain()

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    assert len(motions_registry.getMotions()) == 0
    motions_registry.createMotion(MOTION_CALLDATA_STUB, {"from": easy_track})
    motions = motions_registry.getMotions()
    assert len(motions) == 1
    motion_id = 1
    assert motions[0][0] == motion_id  # id

    # wait motion becomes passed
    motion_duration = motions_registry.motionDuration()
    chain.sleep(motion_duration + 1)

    tx = motions_registry.enactMotion(motion_id, {"from": easy_track})

    # validate that motion was delete and events were emitted
    assert len(motions_registry.getMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionEnacted"]["_motionId"] == motion_id

    # validate that agent wasn't called
    assert not aragon_agent_mock.called()
    assert aragon_agent_mock.data() == "0x"


def test_enact_motion_with_evm_script(
    owner, easy_tracks_registry, motions_registry, aragon_agent_mock
):
    "Must delete motion, emit MotionEnacted"
    "event and forwards script to Aragon agent"

    evm_script_stub_payload = "0xffff"

    chain = Chain()

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    assert len(motions_registry.getMotions()) == 0
    motions_registry.createMotion(MOTION_CALLDATA_STUB, {"from": easy_track})
    motions = motions_registry.getMotions()
    assert len(motions) == 1
    motion_id = 1
    assert motions[0][0] == motion_id  # id

    # wait motion becomes passed
    motion_duration = motions_registry.motionDuration()
    chain.sleep(motion_duration + 1)

    tx = motions_registry.enactMotion(
        motion_id, evm_script_stub_payload, {"from": easy_track}
    )

    # validate that motion was delete and events were emitted
    assert len(motions_registry.getMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionEnacted"]["_motionId"] == motion_id

    # validate that agent was called with correct data
    assert aragon_agent_mock.called()
    assert aragon_agent_mock.data() == evm_script_stub_payload


def test_send_objection_motion_not_found(motions_registry):
    "Must fail with error: 'MOTION_NOT_FOUND'"
    with reverts("MOTION_NOT_FOUND"):
        motions_registry.objectToMotion(1)


def test_send_objection_multiple_times(
    owner, ldo_holders, motions_registry, easy_tracks_registry
):
    "Must fail with error: 'ALREADY_OBJECTED'"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    motions_registry.createMotion("0x", {"from": easy_track})

    # send objection multiple times
    motions_registry.objectToMotion(1, {"from": ldo_holders[0]})
    with reverts("ALREADY_OBJECTED"):
        motions_registry.objectToMotion(1, {"from": ldo_holders[0]})


def test_send_objection_passed_motion(owner, motions_registry, easy_tracks_registry):
    "Must fail with error: 'ERROR_MOTION_PASSED'"
    chain = Chain()

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    motions_registry.createMotion("0x", {"from": easy_track})

    # wait when becomes passed
    motion_duration = motions_registry.motionDuration()
    chain.sleep(motion_duration + 1)

    with reverts("MOTION_PASSED"):
        motions_registry.objectToMotion(1)


def test_send_objection_not_ldo_holder(
    owner, stranger, ldo_token, easy_tracks_registry, motions_registry
):
    "Must fail with error: 'NOT_ENOUGH_BALANCE'"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    motions_registry.createMotion("0x", {"from": easy_track})

    # send objection from user without ldo
    assert ldo_token.balanceOf(stranger) == 0
    with reverts("NOT_ENOUGH_BALANCE"):
        motions_registry.objectToMotion(1, {"from": stranger})


def test_send_objection_by_tokens_holder(
    owner, ldo_holders, ldo_token, easy_tracks_registry, motions_registry
):
    "Must increase motion objections on correct amount and emit ObjectionSent event"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    motions_registry.createMotion("0x", {"from": easy_track})

    # send objection from ldo holder
    tx = motions_registry.objectToMotion(1, {"from": ldo_holders[0]})

    total_supply = ldo_token.totalSupply()
    holder_balance = ldo_token.balanceOf(ldo_holders[0])
    holder_part = 10000 * holder_balance / total_supply

    motion = motions_registry.motions(0)

    assert motion[6] == ldo_token.balanceOf(ldo_holders[0])  # objectionsAmount
    assert motion[7] == holder_part  # objectionsAmountPct

    # validate events
    assert len(tx.events) == 1
    assert tx.events["ObjectionSent"]["_motionId"] == motion[0]
    assert tx.events["ObjectionSent"]["_voterAddress"] == ldo_holders[0]
    assert tx.events["ObjectionSent"]["_weight"] == holder_balance
    assert tx.events["ObjectionSent"]["_votingPower"] == total_supply


def test_send_objection_rejected(
    owner,
    ldo_holders,
    ldo_token,
    easy_tracks_registry,
    motions_registry,
):
    "Must delete motion and emit ObjectionSent and MotionRejected events"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    motions_registry.createMotion("0x", {"from": easy_track})

    # send objections to pass threshold
    motions_registry.objectToMotion(1, {"from": ldo_holders[0]})  # 0.2 % objections
    motions_registry.objectToMotion(1, {"from": ldo_holders[1]})  # 0.4 % objections
    assert len(motions_registry.getMotions()) == 1
    tx = motions_registry.objectToMotion(
        1, {"from": ldo_holders[2]}
    )  # 0.6 % objections
    assert len(motions_registry.getMotions()) == 0

    # validate that events was emitted
    assert len(tx.events) == 2
    assert tx.events["ObjectionSent"]["_motionId"] == 1
    assert tx.events["ObjectionSent"]["_voterAddress"] == ldo_holders[2]
    assert tx.events["ObjectionSent"]["_weight"] == ldo_token.balanceOf(ldo_holders[2])
    assert tx.events["ObjectionSent"]["_votingPower"] == ldo_token.totalSupply()
    assert tx.events["MotionRejected"]["_motionId"] == 1


def test_can_object_to_motion(
    owner,
    stranger,
    ldo_holders,
    easy_tracks_registry,
    motions_registry,
):
    "Must return False if caller has no governance tokens or if he has already voted."
    "Returns True in other cases"

    # add easy track to create motions
    easy_track = accounts[2]
    assert not easy_tracks_registry.isEasyTrack(easy_track)
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert easy_tracks_registry.isEasyTrack(easy_track)

    # create new motion
    motions_registry.createMotion("0x", {"from": easy_track})

    assert not motions_registry.canObjectToMotion(1, stranger)
    assert motions_registry.canObjectToMotion(1, ldo_holders[0])
    motions_registry.objectToMotion(1, {"from": ldo_holders[0]})
    assert not motions_registry.canObjectToMotion(1, ldo_holders[0])


def test_create_evm_script_single_address_single_calldata(
    motions_registry, node_operators_registry_stub
):
    "Must create correct evm script"
    calldata = node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
        1, 200
    )

    evm_script = motions_registry.createEvmScript["address,bytes"](
        node_operators_registry_stub, calldata
    )

    assert evm_script == encode_call_script(
        [(node_operators_registry_stub.address, calldata)]
    )


def test_create_evm_script_single_address_multiple_calldata(
    motions_registry, node_operators_registry_stub
):
    "Must create correct evm script"
    calldata1 = node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
        1, 200
    )
    calldata2 = node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
        2, 300
    )
    calldata3 = node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
        3, 400
    )

    evm_script = motions_registry.createEvmScript["address,bytes[]"](
        node_operators_registry_stub, [calldata1, calldata2, calldata3]
    )

    assert evm_script == encode_call_script(
        [
            (node_operators_registry_stub.address, calldata1),
            (node_operators_registry_stub.address, calldata2),
            (node_operators_registry_stub.address, calldata3),
        ]
    )


def test_create_evm_script_multiple_address_multiple_calldata(
    motions_registry, node_operators_registry_stub
):
    "Must create correct evm script"
    calldata1 = node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
        1, 200
    )
    calldata2 = node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
        2, 300
    )
    calldata3 = node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
        3, 400
    )

    addresses = [accounts[0].address, accounts[1].address, accounts[2].address]

    evm_script = motions_registry.createEvmScript["address[],bytes[]"](
        addresses, [calldata1, calldata2, calldata3]
    )

    assert evm_script == encode_call_script(
        [
            (addresses[0], calldata1),
            (addresses[1], calldata2),
            (addresses[2], calldata3),
        ]
    )
