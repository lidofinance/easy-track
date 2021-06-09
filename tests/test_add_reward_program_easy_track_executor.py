import random

from eth_abi import encode_single
from brownie import AddRewardProgramEasyTrackExecutor, accounts, ZERO_ADDRESS, reverts

import constants
from utils.evm_script import encode_call_script


def test_deploy(owner, easy_tracks_registry, top_up_reward_program_easy_track_executor):
    "Must deploy contract with correct params"

    contract = owner.deploy(
        AddRewardProgramEasyTrackExecutor,
        easy_tracks_registry,
        top_up_reward_program_easy_track_executor,
        owner,
    )

    assert (
        contract.topUpRewardProgramEasyTrackExecutor()
        == top_up_reward_program_easy_track_executor
    )
    assert contract.trustedAddress() == owner
    assert contract.easyTracksRegistry() == easy_tracks_registry


def test_before_create_motion_guard_sender_is_not_easy_tracks_registry(
    stranger,
    add_reward_program_easy_track_executor,
):
    "Must fail with error 'NOT_EASYTRACK_REGISTRY'"
    with reverts("NOT_EASYTRACK_REGISTRY"):
        add_reward_program_easy_track_executor.beforeCreateMotionGuard(
            stranger, "0x", {"from": stranger}
        )


def test_before_create_motion_guard_caller_is_not_trusted_address(
    stranger,
    easy_tracks_registry,
    add_reward_program_easy_track_executor,
):
    "Must fail with error 'ADDRESS_NOT_TRUSTED'"
    with reverts("ADDRESS_NOT_TRUSTED"):
        add_reward_program_easy_track_executor.beforeCreateMotionGuard(
            stranger, "0x", {"from": easy_tracks_registry}
        )


def test_before_create_motion_guard_reward_program_already_added(
    owner,
    stranger,
    easy_tracks_registry,
    add_reward_program_easy_track_executor,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error 'REWARD_PROGRAM_ALREADY_ADDED'"
    reward_program = accounts[6]
    top_up_reward_program_easy_track_executor.initialize(
        add_reward_program_easy_track_executor, owner
    )
    motion_data = encode_single("(address)", [reward_program.address])
    add_reward_program_easy_track_executor.execute(
        motion_data, "0x", {"from": easy_tracks_registry}
    )
    reward_programs = top_up_reward_program_easy_track_executor.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == reward_program

    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        add_reward_program_easy_track_executor.beforeCreateMotionGuard(
            owner, motion_data, {"from": easy_tracks_registry}
        )


def test_before_create_motion_guard_reward(
    owner,
    easy_tracks_registry,
    add_reward_program_easy_track_executor,
    top_up_reward_program_easy_track_executor,
):
    "Must ends without error if caller is trusted address and reward program wasn't added earlier"
    new_reward_program = accounts[6].address
    reward_programs = top_up_reward_program_easy_track_executor.getRewardPrograms()
    assert len(reward_programs) == 0
    add_reward_program_easy_track_executor.beforeCreateMotionGuard(
        owner,
        encode_single("(address)", [new_reward_program]),
        {"from": easy_tracks_registry},
    )


def test_before_cancel_motion_guard_sender_is_not_easy_tracks_registry(
    stranger,
    add_reward_program_easy_track_executor,
):
    "Must fail with error 'NOT_EASYTRACK_REGISTRY'"
    with reverts("NOT_EASYTRACK_REGISTRY"):
        add_reward_program_easy_track_executor.beforeCancelMotionGuard(
            stranger, "0x", "0x", {"from": stranger}
        )


def test_before_cancel_motion_guard_caller_is_not_trusted_address(
    stranger,
    easy_tracks_registry,
    add_reward_program_easy_track_executor,
):
    "Must fail with error 'ADDRESS_NOT_TRUSTED'"
    with reverts("ADDRESS_NOT_TRUSTED"):
        add_reward_program_easy_track_executor.beforeCancelMotionGuard(
            stranger, "0x", "0x", {"from": easy_tracks_registry}
        )


def test_before_cancel_motion_guard_caller(
    owner,
    easy_tracks_registry,
    add_reward_program_easy_track_executor,
):
    "Must ends without error if caller is trusted address and called by easy tracks registry"
    add_reward_program_easy_track_executor.beforeCancelMotionGuard(
        owner, "0x", "0x", {"from": easy_tracks_registry}
    )


def test_execute_sender_is_not_easy_tracks_registry(
    stranger,
    add_reward_program_easy_track_executor,
):
    "Must fail with error 'NOT_EASYTRACK_REGISTRY'"

    reward_program = accounts[7].address
    motion_data = encode_single("(address)", [reward_program])

    with reverts("NOT_EASYTRACK_REGISTRY"):
        add_reward_program_easy_track_executor.execute(
            motion_data, "0x", {"from": stranger}
        )


def test_execute(
    owner,
    easy_tracks_registry,
    add_reward_program_easy_track_executor,
    top_up_reward_program_easy_track_executor,
):
    "Must add new reward program to top up reward program easy track executor"

    reward_program = accounts[7].address
    motion_data = encode_single("(address)", [reward_program])

    top_up_reward_program_easy_track_executor.initialize(
        add_reward_program_easy_track_executor, owner
    )

    reward_programs = top_up_reward_program_easy_track_executor.getRewardPrograms()
    assert len(reward_programs) == 0

    add_reward_program_easy_track_executor.execute(
        motion_data, "0x", {"from": easy_tracks_registry}
    )

    reward_programs = top_up_reward_program_easy_track_executor.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == reward_program
