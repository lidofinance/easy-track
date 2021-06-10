import random

from eth_abi import encode_single
from brownie import LegoEasyTrackExecutor, accounts, ZERO_ADDRESS, reverts

import constants
from utils.evm_script import encode_call_script


def test_deploy(
    owner,
    finance,
    ldo_token,
    steth_token,
    lego_program,
    easy_tracks_registry,
):
    "Must deploy contract with correct params"

    contract = owner.deploy(
        LegoEasyTrackExecutor,
        easy_tracks_registry,
        owner,
        finance,
        lego_program,
        ldo_token,
        steth_token,
    )

    assert contract.easyTracksRegistry() == easy_tracks_registry
    assert contract.trustedAddress() == owner
    assert contract.finance() == finance
    assert contract.legoProgram() == lego_program
    assert contract.tokens(0) == ldo_token
    assert contract.tokens(1) == steth_token


def test_before_create_motion_guard_sender_is_not_easy_tracks_registry(
    stranger,
    lego_reward_program_easy_track_executor,
):
    "Must fail with error 'NOT_EASYTRACK_REGISTRY'"
    with reverts("NOT_EASYTRACK_REGISTRY"):
        lego_reward_program_easy_track_executor.beforeCreateMotionGuard(
            stranger, "0x", {"from": stranger}
        )


def test_before_create_motion_guard_caller_is_not_trusted_address(
    stranger,
    easy_tracks_registry,
    lego_reward_program_easy_track_executor,
):
    "Must fail with error 'ADDRESS_NOT_TRUSTED'"
    with reverts("ADDRESS_NOT_TRUSTED"):
        lego_reward_program_easy_track_executor.beforeCreateMotionGuard(
            stranger, "0x", {"from": easy_tracks_registry}
        )


def test_before_create_motion_guard_all_amounts_zero(
    owner,
    easy_tracks_registry,
    lego_reward_program_easy_track_executor,
):
    "Must fail with error 'ALL_AMOUNTS_ZERO'"
    motion_data = encode_single("(uint256,uint256,uint256)", [0, 0, 0])
    with reverts("ALL_AMOUNTS_ZERO"):
        lego_reward_program_easy_track_executor.beforeCreateMotionGuard(
            owner, motion_data, {"from": easy_tracks_registry}
        )


def test_before_create_motion_guard(
    owner,
    easy_tracks_registry,
    lego_reward_program_easy_track_executor,
):
    "Must ends without error if caller is trusted address and some amount of tokens greater than zero"
    motion_data = encode_single("(uint256,uint256,uint256)", [1 ** 18, 0, 0])
    lego_reward_program_easy_track_executor.beforeCreateMotionGuard(
        owner, motion_data, {"from": easy_tracks_registry}
    )


def test_before_cancel_motion_guard_sender_is_not_easy_tracks_registry(
    stranger,
    lego_reward_program_easy_track_executor,
):
    "Must fail with error 'NOT_EASYTRACK_REGISTRY'"
    with reverts("NOT_EASYTRACK_REGISTRY"):
        lego_reward_program_easy_track_executor.beforeCancelMotionGuard(
            stranger, "0x", "0x", {"from": stranger}
        )


def test_before_cancel_motion_guard_caller_is_not_trusted_address(
    stranger,
    easy_tracks_registry,
    lego_reward_program_easy_track_executor,
):
    "Must fail with error 'ADDRESS_NOT_TRUSTED'"
    with reverts("ADDRESS_NOT_TRUSTED"):
        lego_reward_program_easy_track_executor.beforeCancelMotionGuard(
            stranger, "0x", "0x", {"from": easy_tracks_registry}
        )


def test_before_cancel_motion_guard(
    owner,
    easy_tracks_registry,
    lego_reward_program_easy_track_executor,
):
    "Must ends without error if caller is trusted address and called by easy tracks registry"
    lego_reward_program_easy_track_executor.beforeCancelMotionGuard(
        owner, "0x", "0x", {"from": easy_tracks_registry}
    )


def test_execute_sender_is_not_easy_tracks_registry(
    stranger,
    lego_reward_program_easy_track_executor,
):
    "Must fail with error 'NOT_EASYTRACK_REGISTRY'"

    reward_program = accounts[7].address
    motion_data = encode_single("(address)", [reward_program])

    with reverts("NOT_EASYTRACK_REGISTRY"):
        lego_reward_program_easy_track_executor.execute(
            motion_data, "0x", {"from": stranger}
        )


def test_execute_all_amounts_iz_zero(
    owner,
    easy_tracks_registry,
    lego_reward_program_easy_track_executor,
):
    "Must fail with error 'ALL_AMOUNTS_ZERO'"
    motion_data = encode_single("(uint256,uint256,uint256)", [0, 0, 0])
    with reverts("ALL_AMOUNTS_ZERO"):
        lego_reward_program_easy_track_executor.execute(
            motion_data, "0x", {"from": easy_tracks_registry}
        )


def test_execute(
    owner,
    finance,
    lego_program,
    easy_tracks_registry,
    lego_reward_program_easy_track_executor,
):
    "Must create correct evmScript"
    amounts = [10 ** 18, 2 * 10 ** 18, 3 * 10 ** 18]
    motion_data = encode_single("(uint256,uint256,uint256)", amounts)

    evm_script = lego_reward_program_easy_track_executor.execute.call(
        motion_data, "0x", {"from": easy_tracks_registry}
    )

    expected_script = encode_call_script(
        [
            (
                constants.FINANCE,
                finance.newImmediatePayment.encode_input(
                    constants.LDO_TOKEN,
                    lego_program.address,
                    amounts[0],
                    "Lego Program Transfer",
                ),
            ),
            (
                constants.FINANCE,
                finance.newImmediatePayment.encode_input(
                    constants.STETH_TOKEN,
                    lego_program.address,
                    amounts[1],
                    "Lego Program Transfer",
                ),
            ),
            (
                constants.FINANCE,
                finance.newImmediatePayment.encode_input(
                    ZERO_ADDRESS,
                    lego_program.address,
                    amounts[2],
                    "Lego Program Transfer",
                ),
            ),
        ]
    )
    assert evm_script == expected_script
