import random

from eth_abi import encode_single
from brownie import TopUpRewardProgramEasyTrack, accounts, ZERO_ADDRESS, reverts

import constants
from utils.evm_script import encode_call_script

MOTION_ID = 2


def test_deploy(owner, motions_registry, finance, ldo_token):
    "Must deploy contract with correct params"

    contract = owner.deploy(
        TopUpRewardProgramEasyTrack, motions_registry, owner, finance, ldo_token
    )

    assert contract.trustedSender() == owner
    assert contract.finance() == finance
    assert contract.rewardToken() == ldo_token
    assert contract.motionsRegistry() == motions_registry

    assert contract.addRewardProgramEasyTrack() == ZERO_ADDRESS
    assert contract.removeRewardProgramEasyTrack() == ZERO_ADDRESS


def test_initialize(top_up_reward_program_easy_track):
    "Must set addRewardProgramEasyTrack and deleteRewardProgramEasyTrack"
    "variables and fail with error 'ALREADY_INITIALIZED' on repeated call"

    add_reward_program_easy_track = accounts[0]
    remove_reward_program_easy_track = accounts[1]

    assert top_up_reward_program_easy_track.addRewardProgramEasyTrack() == ZERO_ADDRESS
    assert (
        top_up_reward_program_easy_track.removeRewardProgramEasyTrack() == ZERO_ADDRESS
    )

    top_up_reward_program_easy_track.initialize(
        add_reward_program_easy_track, remove_reward_program_easy_track
    )

    assert (
        top_up_reward_program_easy_track.addRewardProgramEasyTrack()
        == add_reward_program_easy_track
    )
    assert (
        top_up_reward_program_easy_track.removeRewardProgramEasyTrack()
        == remove_reward_program_easy_track
    )

    with reverts("ALREADY_INITIALIZED"):
        top_up_reward_program_easy_track.initialize(
            add_reward_program_easy_track, remove_reward_program_easy_track
        )


def test_add_reward_program_called_by_stranger(
    owner, stranger, top_up_reward_program_easy_track
):
    "Must fail with error 'FORBIDDEN' error"
    top_up_reward_program_easy_track.initialize(owner, owner)
    with reverts("FORBIDDEN"):
        top_up_reward_program_easy_track.addRewardProgram(stranger, {"from": stranger})


def test_add_reward_program(owner, stranger, top_up_reward_program_easy_track):
    "Must add new reward program to rewardPrograms array and fail with"
    "error 'REWARD_PROGRAM_ALREADY_ADDED' error on call with same reward program"
    top_up_reward_program_easy_track.initialize(owner, owner)
    top_up_reward_program_easy_track.addRewardProgram(stranger, {"from": owner})

    reward_programs = top_up_reward_program_easy_track.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == stranger

    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        top_up_reward_program_easy_track.addRewardProgram(stranger, {"from": owner})


def test_remove_reward_program_called_by_stranger(
    owner, stranger, top_up_reward_program_easy_track
):
    "Must fail with error 'FORBIDDEN' error"
    top_up_reward_program_easy_track.initialize(owner, owner)
    with reverts("FORBIDDEN"):
        top_up_reward_program_easy_track.removeRewardProgram(
            stranger, {"from": stranger}
        )


def test_remove_reward_program_with_not_existed_reward_program(
    owner, top_up_reward_program_easy_track
):
    "Must fail with error 'REWARD_PROGRAM_NOT_FOUND' error"
    top_up_reward_program_easy_track.initialize(owner, owner)
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        top_up_reward_program_easy_track.removeRewardProgram(owner, {"from": owner})


def test_remove_reward_program(owner, top_up_reward_program_easy_track):
    "Must remove reward program from the list of allowed programs"
    top_up_reward_program_easy_track.initialize(owner, owner)

    reward_programs = accounts[4:9]

    for reward_program in reward_programs:
        top_up_reward_program_easy_track.addRewardProgram(
            reward_program, {"from": owner}
        )

    while len(reward_programs) > 0:
        index_to_delete = random.randint(0, len(reward_programs) - 1)
        reward_program = reward_programs.pop(index_to_delete)

        top_up_reward_program_easy_track.removeRewardProgram(
            reward_program, {"from": owner}
        )

        contract_reward_programs = top_up_reward_program_easy_track.getRewardPrograms()
        assert len(reward_programs) == len(contract_reward_programs)

        # validate that was deleted correct address by join
        # test set with resulting set their size must be same
        assert len(set(reward_programs).union(contract_reward_programs)) == len(
            contract_reward_programs
        )


def test_is_allowed(owner, top_up_reward_program_easy_track):
    top_up_reward_program_easy_track.initialize(owner, owner)
    reward_program = accounts[7]
    assert not top_up_reward_program_easy_track.isAllowed(reward_program)
    top_up_reward_program_easy_track.addRewardProgram(reward_program, {"from": owner})
    assert top_up_reward_program_easy_track.isAllowed(reward_program)


def test_create_motion_called_by_stranger(stranger, top_up_reward_program_easy_track):
    "Must fail with error 'SENDER_NOT_TRUSTED'"

    with reverts("SENDER_NOT_TRUSTED"):
        top_up_reward_program_easy_track.createMotion([], [], {"from": stranger})


def test_create_motion_data_length_mismatch(owner, top_up_reward_program_easy_track):
    "Must fail with error 'LENGTH_MISMATCH'"

    with reverts("LENGTH_MISMATCH"):
        top_up_reward_program_easy_track.createMotion(
            [accounts[0], accounts[1]], [1 ** 18], {"from": owner}
        )


def test_create_motion_empty_data(owner, top_up_reward_program_easy_track):
    "Must fail with error 'EMPTY_DATA'"

    with reverts("EMPTY_DATA"):
        top_up_reward_program_easy_track.createMotion([], [], {"from": owner})


def test_create_motion_zero_amount(owner, top_up_reward_program_easy_track):
    "Must fail with error 'ZERO_AMOUNT'"
    reward_programs = [accounts[0], accounts[1]]
    amounts = [1 ** 18, 0]

    top_up_reward_program_easy_track.initialize(owner, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[0], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[1], {"from": owner}
    )

    with reverts("ZERO_AMOUNT"):
        top_up_reward_program_easy_track.createMotion(
            reward_programs, amounts, {"from": owner}
        )


def test_create_motion_reward_program_not_allowed(
    owner, top_up_reward_program_easy_track
):
    "Must fail with error 'REWARD_PROGRAM_NOT_FOUND'"

    not_allowed_reward_program = accounts[3]
    reward_programs = [accounts[1], accounts[4], accounts[2]]
    amounts = [1 ** 18, 2 * 1 ** 18, 3 * 1 ** 18]

    # empty reward programs edge case
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        top_up_reward_program_easy_track.createMotion(
            reward_programs[0:1], amounts[0:1], {"from": owner}
        )

    top_up_reward_program_easy_track.initialize(owner, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[0], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[1], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[2], {"from": owner}
    )

    # case with added reward programs
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        top_up_reward_program_easy_track.createMotion(
            [reward_programs[0], reward_programs[1], not_allowed_reward_program],
            amounts,
            {"from": owner},
        )


def test_create_motion(owner, top_up_reward_program_easy_track, motions_registry_stub):
    "Must pass correct data to motionsRegistry.createMotion"
    reward_programs = [accounts[1].address, accounts[2].address]
    amounts = [1 ** 18, 2 * 1 ** 18]
    # add reward programs
    top_up_reward_program_easy_track.initialize(owner, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[0], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[1], {"from": owner}
    )

    assert not motions_registry_stub.createMotionCalled()
    # create motion
    top_up_reward_program_easy_track.createMotion(reward_programs, amounts)
    assert motions_registry_stub.createMotionCalled()
    assert motions_registry_stub.motionData() == encode_motion_data(
        reward_programs, amounts
    )


def test_cancel_motion_called_by_stranger(stranger, top_up_reward_program_easy_track):
    "Must fail with error 'SENDER_NOT_TRUSTED'"

    with reverts("SENDER_NOT_TRUSTED"):
        top_up_reward_program_easy_track.cancelMotion(1, {"from": stranger})


def test_cancel_motion(owner, top_up_reward_program_easy_track, motions_registry_stub):
    "Must call motionsRegistry.cancelMotion method with"
    "correct motionId when called by trusted sender"

    assert not motions_registry_stub.cancelMotionCalled()
    top_up_reward_program_easy_track.cancelMotion(MOTION_ID, {"from": owner})
    assert motions_registry_stub.cancelMotionCalled()
    assert motions_registry_stub.cancelMotionId() == MOTION_ID


def test_enact_motion_data_length_mismatch(
    owner, top_up_reward_program_easy_track, motions_registry_stub
):
    "Must fail with error 'LENGTH_MISMATCH'"

    reward_programs = [accounts[0].address, accounts[1].address]
    # prepare motions registry stub
    motions_registry_stub.setMotionData(encode_motion_data(reward_programs, [1 ** 18]))

    with reverts("LENGTH_MISMATCH"):
        top_up_reward_program_easy_track.enactMotion(MOTION_ID, {"from": owner})


def test_enact_motion_empty_data(
    owner, top_up_reward_program_easy_track, motions_registry_stub
):
    "Must fail with error 'EMPTY_DATA'"

    # prepare motions registry stub
    motions_registry_stub.setMotionData(encode_motion_data([], []))

    with reverts("EMPTY_DATA"):
        top_up_reward_program_easy_track.enactMotion(MOTION_ID, {"from": owner})


def test_enact_motion_zero_amount(
    owner, top_up_reward_program_easy_track, motions_registry_stub
):
    "Must fail with error 'ZERO_AMOUNT'"
    reward_programs = [accounts[0].address, accounts[1].address]
    amounts = [1 ** 18, 0]

    top_up_reward_program_easy_track.initialize(owner, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[0], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[1], {"from": owner}
    )

    # prepare motions registry stub
    motions_registry_stub.setMotionData(encode_motion_data(reward_programs, amounts))

    with reverts("ZERO_AMOUNT"):
        top_up_reward_program_easy_track.enactMotion(MOTION_ID, {"from": owner})


def test_enact_motion_reward_program_not_allowed(
    owner, top_up_reward_program_easy_track, motions_registry_stub
):
    "Must fail with error 'REWARD_PROGRAM_NOT_FOUND'"

    not_allowed_reward_program = accounts[3].address
    reward_programs = [accounts[1].address, accounts[4].address, accounts[2].address]
    amounts = [1 ** 18, 2 * 1 ** 18, 3 * 1 ** 18]

    top_up_reward_program_easy_track.initialize(owner, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[0], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[1], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[2], {"from": owner}
    )

    # prepare motions registry stub
    motions_registry_stub.setMotionData(
        encode_motion_data(
            [reward_programs[0], reward_programs[1], not_allowed_reward_program],
            amounts,
        )
    )

    # case with added reward programs
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        top_up_reward_program_easy_track.enactMotion(MOTION_ID, {"from": owner})


def test_enact_motion(
    owner, finance, ldo_token, top_up_reward_program_easy_track, motions_registry_stub
):
    "Must pass correct motionId and evm script to motionsRegistry.enactMotion"
    reward_programs = [accounts[1].address, accounts[2].address]
    amounts = [1 ** 18, 2 * 1 ** 18]

    # add reward programs
    top_up_reward_program_easy_track.initialize(owner, owner)
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[0], {"from": owner}
    )
    top_up_reward_program_easy_track.addRewardProgram(
        reward_programs[1], {"from": owner}
    )

    # prepare motions registry stub
    motions_registry_stub.setMotionData(encode_motion_data(reward_programs, amounts))

    assert not motions_registry_stub.enactMotionCalled()
    top_up_reward_program_easy_track.enactMotion(MOTION_ID, {"from": owner})
    assert motions_registry_stub.enactMotionCalled()
    assert motions_registry_stub.enactMotionId() == MOTION_ID
    assert motions_registry_stub.evmScript() == encode_call_script(
        [
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    ldo_token, reward_programs[0], amounts[0], "Reward program top up"
                ),
            ),
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    ldo_token, reward_programs[1], amounts[1], "Reward program top up"
                ),
            ),
        ]
    )


def encode_motion_data(reward_programs, amounts):
    return (
        "0x" + encode_single("(address[],uint256[])", [reward_programs, amounts]).hex()
    )
