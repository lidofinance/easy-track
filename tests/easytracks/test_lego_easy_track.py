import random

from eth_abi import encode_single
from brownie import LegoEasyTrack, accounts, ZERO_ADDRESS, reverts

import constants
from utils.evm_script import encode_call_script

MOTION_ID = 2


def test_deploy(owner, finance, lego_program, motions_registry):
    "Must deploy contract with correct params"

    contract = owner.deploy(
        LegoEasyTrack, motions_registry, owner, finance, lego_program
    )

    assert contract.trustedSender() == owner
    assert contract.motionsRegistry() == motions_registry
    assert contract.finance() == finance
    assert contract.legoProgram() == lego_program


def test_create_motion_called_by_stranger(stranger, lego_easy_track):
    "Must fail with error 'SENDER_NOT_TRUSTED'"

    tokens = []
    amounts = []

    with reverts("SENDER_NOT_TRUSTED"):
        lego_easy_track.createMotion(tokens, amounts, {"from": stranger})


def test_create_motion_lengths_mismatch(owner, ldo_token, lego_easy_track):
    "Must fail with error 'LENGTHS_MISMATCH'"

    tokens = [ldo_token]
    amounts = []

    with reverts("LENGTHS_MISMATCH"):
        lego_easy_track.createMotion(tokens, amounts, {"from": owner})


def test_create_motion_empty_data(owner, lego_easy_track):
    "Must fail with error 'EMPTY_DATA'"

    tokens = []
    amounts = []

    with reverts("EMPTY_DATA"):
        lego_easy_track.createMotion(tokens, amounts, {"from": owner})


def test_create_motion_zero_amount(owner, ldo_token, lego_easy_track):
    "Must fail with error 'ZERO_AMOUNT'"

    tokens = [ldo_token]
    amounts = [0]

    with reverts("ZERO_AMOUNT"):
        lego_easy_track.createMotion(tokens, amounts, {"from": owner})


def test_create_motion(
    owner, ldo_token, steth_token, lego_easy_track, motions_registry_stub
):
    "Must call motionsRegistry.createMotion with correct motion data"

    tokens = [ldo_token.address, ZERO_ADDRESS, steth_token.address]
    amounts = [1 ** 18, 2 * 1 ** 18, 3 * 1 ** 18]

    assert not motions_registry_stub.createMotionCalled()
    lego_easy_track.createMotion(tokens, amounts, {"from": owner})
    assert motions_registry_stub.createMotionCalled()
    assert motions_registry_stub.motionData() == encode_motion_data(tokens, amounts)


def test_cancel_motion_called_by_stranger(stranger, lego_easy_track):
    "Must fail with error 'SENDER_NOT_TRUSTED'"

    with reverts("SENDER_NOT_TRUSTED"):
        lego_easy_track.cancelMotion(1, {"from": stranger})


def test_cancel_motion(owner, lego_easy_track, motions_registry_stub):
    "Must call motionsRegistry.cancelMotion method with"
    "correct motionId when called by trusted sender"

    assert not motions_registry_stub.cancelMotionCalled()
    lego_easy_track.cancelMotion(MOTION_ID, {"from": owner})
    assert motions_registry_stub.cancelMotionCalled()
    assert motions_registry_stub.cancelMotionId() == MOTION_ID


def test_enact_motion_lengths_mismatch(
    owner, ldo_token, lego_easy_track, motions_registry_stub
):
    "Must fail with error 'LENGTHS_MISMATCH'"

    # prepare motions registry stub
    tokens = [ldo_token.address]
    amounts = []
    motions_registry_stub.setMotionData(encode_motion_data(tokens, amounts))

    with reverts("LENGTHS_MISMATCH"):
        lego_easy_track.enactMotion(MOTION_ID, {"from": owner})


def test_enact_motion_empty_data(owner, lego_easy_track, motions_registry_stub):
    "Must fail with error 'EMPTY_DATA'"

    # prepare motions registry stub
    tokens = []
    amounts = []
    motions_registry_stub.setMotionData(encode_motion_data(tokens, amounts))

    with reverts("EMPTY_DATA"):
        lego_easy_track.enactMotion(MOTION_ID, {"from": owner})


def test_enact_motion_zero_amount(
    owner, ldo_token, lego_easy_track, motions_registry_stub
):
    "Must fail with error 'ZERO_AMOUNT'"

    # prepare motions registry stub
    tokens = [ldo_token.address]
    amounts = [0]
    motions_registry_stub.setMotionData(encode_motion_data(tokens, amounts))

    with reverts("ZERO_AMOUNT"):
        lego_easy_track.enactMotion(MOTION_ID, {"from": owner})


def test_enact_motion(
    owner,
    finance,
    ldo_token,
    steth_token,
    lego_program,
    lego_easy_track,
    motions_registry_stub,
):
    "Must pass correct motionId and evm script to motionsRegistry.enactMotion"

    # prepare motions registry stub
    tokens = [ldo_token.address, ZERO_ADDRESS, steth_token.address]
    amounts = [1 ** 18, 2 * 1 ** 18, 3 * 1 ** 18]
    motions_registry_stub.setMotionData(encode_motion_data(tokens, amounts))

    assert not motions_registry_stub.enactMotionCalled()
    lego_easy_track.enactMotion(MOTION_ID, {"from": owner})
    assert motions_registry_stub.enactMotionCalled()
    assert motions_registry_stub.enactMotionId() == MOTION_ID
    assert motions_registry_stub.evmScript() == encode_call_script(
        [
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    tokens[0], lego_program.address, amounts[0], "Lego Program Transfer"
                ),
            ),
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    tokens[1], lego_program.address, amounts[1], "Lego Program Transfer"
                ),
            ),
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    tokens[2], lego_program.address, amounts[2], "Lego Program Transfer"
                ),
            ),
        ]
    )


def encode_motion_data(tokens, amounts):
    return "0x" + encode_single("(address[],uint256[])", [tokens, amounts]).hex()
