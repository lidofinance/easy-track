import random

from eth_abi import encode_single
from brownie import AddRewardProgramEasyTrack, accounts, ZERO_ADDRESS, reverts

import constants
from utils.evm_script import encode_call_script

MOTION_ID = 1


def test_deploy(owner, motions_registry, top_up_reward_program_easy_track):
    "Must deploy contract with correct params"

    contract = owner.deploy(
        AddRewardProgramEasyTrack,
        motions_registry,
        owner,
        top_up_reward_program_easy_track,
    )

    assert contract.trustedSender() == owner
    assert contract.motionsRegistry() == motions_registry
    assert contract.topUpRewardProgramEasyTrack() == top_up_reward_program_easy_track


def test_create_motion_called_by_stranger(stranger, add_reward_program_easy_track):
    "Must fail with error 'SENDER_NOT_TRUSTED'"

    with reverts("SENDER_NOT_TRUSTED"):
        add_reward_program_easy_track.createMotion(accounts[0], {"from": stranger})


def test_create_motion_reward_program_already_added(
    owner, add_reward_program_easy_track, top_up_reward_program_easy_track
):
    "Must fail with error 'ALREADY_ALLOWED'"

    # initialize top_up_reward_program_easy_track
    reward_program = accounts[3]
    top_up_reward_program_easy_track.initialize(add_reward_program_easy_track, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_program, {"from": add_reward_program_easy_track}
    )

    with reverts("ALREADY_ALLOWED"):
        add_reward_program_easy_track.createMotion(reward_program, {"from": owner})


def test_create_motion(
    owner,
    add_reward_program_easy_track,
    top_up_reward_program_easy_track,
    motions_registry_stub,
):
    "Must call motionsRegistry.createMotion with correct data"

    # initialize top_up_reward_program_easy_track
    reward_program = accounts[3].address
    top_up_reward_program_easy_track.initialize(add_reward_program_easy_track, owner)

    assert not motions_registry_stub.createMotionCalled()
    add_reward_program_easy_track.createMotion(reward_program, {"from": owner})
    assert motions_registry_stub.createMotionCalled()
    assert motions_registry_stub.motionData() == encode_motion_data(reward_program)


def test_cancel_motion_called_by_stranger(stranger, add_reward_program_easy_track):
    "Must fail with error 'SENDER_NOT_TRUSTED'"

    with reverts("SENDER_NOT_TRUSTED"):
        add_reward_program_easy_track.cancelMotion(1, {"from": stranger})


def test_cancel_motion(owner, add_reward_program_easy_track, motions_registry_stub):
    "Must call motionsRegistry.cancelMotion method with"
    "correct motionId when called by trusted sender"

    assert not motions_registry_stub.cancelMotionCalled()
    add_reward_program_easy_track.cancelMotion(MOTION_ID, {"from": owner})
    assert motions_registry_stub.cancelMotionCalled()
    assert motions_registry_stub.cancelMotionId() == MOTION_ID


def test_enact_motion_reward_program_already_added(
    owner,
    stranger,
    add_reward_program_easy_track,
    top_up_reward_program_easy_track,
    motions_registry_stub,
):
    "Must fail with error 'ALREADY_ALLOWED'"

    reward_program = accounts[3].address

    # prepare motions registry stub
    motions_registry_stub.setMotionData(encode_motion_data(reward_program))

    # initialize top_up_reward_program_easy_track
    top_up_reward_program_easy_track.initialize(add_reward_program_easy_track, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_program, {"from": add_reward_program_easy_track}
    )

    with reverts("ALREADY_ALLOWED"):
        add_reward_program_easy_track.enactMotion(MOTION_ID, {"from": stranger})


def test_enact_motion(
    owner,
    stranger,
    add_reward_program_easy_track,
    top_up_reward_program_easy_track,
    motions_registry_stub,
):
    "Must add reward program to list of allowed reward programs and"
    "pass correct motionId to motionsRegistry.enactMotion"

    reward_program = accounts[3].address

    # initialize top_up_reward_program_easy_track
    top_up_reward_program_easy_track.initialize(add_reward_program_easy_track, owner)

    # prepare motions registry stub
    motions_registry_stub.setMotionData(encode_motion_data(reward_program))

    assert not motions_registry_stub.enactMotionCalled()
    assert not top_up_reward_program_easy_track.isAllowed(reward_program)
    add_reward_program_easy_track.enactMotion(MOTION_ID, {"from": stranger})

    assert motions_registry_stub.enactMotionCalled()
    assert motions_registry_stub.enactMotionId() == MOTION_ID
    assert motions_registry_stub.evmScript() == "0x"

    assert top_up_reward_program_easy_track.isAllowed(reward_program)


def encode_motion_data(reward_program):
    return "0x" + encode_single("(address)", [reward_program]).hex()
