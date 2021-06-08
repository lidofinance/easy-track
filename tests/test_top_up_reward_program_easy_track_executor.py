import random

from eth_abi import encode_single
from brownie import TopUpRewardProgramEasyTrackExecutor, accounts, ZERO_ADDRESS, reverts

import constants
from utils.evm_script import encode_call_script


def test_deploy(
    owner,
    easy_tracks_registry,
):
    "Must deploy contract with correct params"

    contract = owner.deploy(
        TopUpRewardProgramEasyTrackExecutor,
        easy_tracks_registry,
        owner,
        constants.FINANCE,
        constants.LDO_TOKEN,
    )

    assert contract.finance() == constants.FINANCE
    assert contract.rewardToken() == constants.LDO_TOKEN
    assert contract.trustedAddress() == owner
    assert contract.easyTracksRegistry() == easy_tracks_registry

    assert contract.addRewardProgramEasyTrackExecutor() == ZERO_ADDRESS
    assert contract.removeRewardProgramEasyTrackExecutor() == ZERO_ADDRESS


def test_initialize(top_up_reward_program_easy_track_executor):
    "Must set addRewardProgramEasyTrackExecutor and deleteRewardProgramEasyTrackExecutor"
    "variables and fail with error 'ALREADY_INITIALIZED' on repeated call"

    add_reward_program_easy_track_executor = accounts[0]
    remove_reward_program_easy_track_executor = accounts[1]

    assert (
        top_up_reward_program_easy_track_executor.addRewardProgramEasyTrackExecutor()
        == ZERO_ADDRESS
    )
    assert (
        top_up_reward_program_easy_track_executor.removeRewardProgramEasyTrackExecutor()
        == ZERO_ADDRESS
    )

    top_up_reward_program_easy_track_executor.initialize(
        add_reward_program_easy_track_executor,
        remove_reward_program_easy_track_executor,
    )

    assert (
        top_up_reward_program_easy_track_executor.addRewardProgramEasyTrackExecutor()
        == add_reward_program_easy_track_executor
    )
    assert (
        top_up_reward_program_easy_track_executor.removeRewardProgramEasyTrackExecutor()
        == remove_reward_program_easy_track_executor
    )

    with reverts("ALREADY_INITIALIZED"):
        top_up_reward_program_easy_track_executor.initialize(
            add_reward_program_easy_track_executor,
            remove_reward_program_easy_track_executor,
        )


def test_add_reward_program_called_by_stranger(
    stranger,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error 'FORBIDDEN' error"
    top_up_reward_program_easy_track_executor.initialize(
        accounts[0],
        accounts[1],
    )
    with reverts("FORBIDDEN"):
        top_up_reward_program_easy_track_executor.addRewardProgram(
            stranger, {"from": stranger}
        )


def test_add_reward_program(
    owner,
    stranger,
    top_up_reward_program_easy_track_executor,
):
    "Must add new reward program to rewardPrograms array and fail with"
    "error 'REWARD_PROGRAM_ALREADY_ADDED' error on call with same reward program"
    top_up_reward_program_easy_track_executor.initialize(
        owner,
        owner,
    )
    top_up_reward_program_easy_track_executor.addRewardProgram(
        stranger, {"from": owner}
    )

    reward_programs = top_up_reward_program_easy_track_executor.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == stranger

    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        top_up_reward_program_easy_track_executor.addRewardProgram(
            stranger, {"from": owner}
        )


def test_remove_reward_program_called_by_stranger(
    owner,
    stranger,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error 'FORBIDDEN' error"
    top_up_reward_program_easy_track_executor.initialize(owner, owner)
    with reverts("FORBIDDEN"):
        top_up_reward_program_easy_track_executor.removeRewardProgram(
            stranger, {"from": stranger}
        )


def test_remove_reward_program_with_not_existed_reward_program(
    owner,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error 'REWARD_PROGRAM_NOT_FOUND' error"
    top_up_reward_program_easy_track_executor.initialize(owner, owner)
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        top_up_reward_program_easy_track_executor.removeRewardProgram(
            owner, {"from": owner}
        )


def test_remove_reward_program(
    owner,
    top_up_reward_program_easy_track_executor,
):
    "Must remove reward program from the list of allowed programs"
    top_up_reward_program_easy_track_executor.initialize(
        owner,
        owner,
    )

    reward_programs = accounts[4:9]

    for reward_program in reward_programs:
        top_up_reward_program_easy_track_executor.addRewardProgram(
            reward_program, {"from": owner}
        )

    while len(reward_programs) > 0:
        index_to_delete = random.randint(0, len(reward_programs) - 1)
        reward_program = reward_programs.pop(index_to_delete)

        top_up_reward_program_easy_track_executor.removeRewardProgram(
            reward_program, {"from": owner}
        )

        contract_reward_programs = (
            top_up_reward_program_easy_track_executor.getRewardPrograms()
        )
        assert len(reward_programs) == len(contract_reward_programs)

        # validate that was deleted correct address by join
        # test set with resulting set their size must be same
        assert len(set(reward_programs).union(contract_reward_programs)) == len(
            contract_reward_programs
        )


def test_is_allowed(
    owner,
    top_up_reward_program_easy_track_executor,
):
    top_up_reward_program_easy_track_executor.initialize(
        owner,
        owner,
    )
    reward_program = accounts[7]
    assert not top_up_reward_program_easy_track_executor.isAllowed(reward_program)
    top_up_reward_program_easy_track_executor.addRewardProgram(
        reward_program, {"from": owner}
    )
    assert top_up_reward_program_easy_track_executor.isAllowed(reward_program)


def test_before_create_motion_guard_caller_not_trusted_address(
    stranger,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error: 'ADDRESS_NOT_TRUSTED'"
    with reverts("ADDRESS_NOT_TRUSTED"):
        top_up_reward_program_easy_track_executor.beforeCreateMotionGuard(
            stranger, "0x", {"from": easy_tracks_registry}
        )


def test_before_create_motion_guard_reward_program_not_found(
    owner,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error 'REWARD_PROGRAM_NOT_FOUND' error"
    top_up_reward_program_easy_track_executor.initialize(
        owner,
        owner,
    )

    reward_programs = accounts[4:6]

    top_up_reward_program_easy_track_executor.addRewardProgram(
        reward_programs[0], {"from": owner}
    )
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        top_up_reward_program_easy_track_executor.beforeCreateMotionGuard(
            owner,
            encode_single(
                "(address[],uint256[])",
                ([reward_programs[0].address, reward_programs[1].address], [512, 1024]),
            ),
            {"from": easy_tracks_registry},
        )


def test_before_create_motion_guard_empty_payload(
    owner,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error: 'INVALID_LENGTH'"
    with reverts("INVALID_LENGTH"):
        top_up_reward_program_easy_track_executor.beforeCreateMotionGuard(
            owner,
            encode_single("(address[],uint256[])", ([], [])),
            {"from": easy_tracks_registry},
        )


def test_before_create_motion_guard_missmatched_length(
    owner,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error: 'INVALID_LENGTH'"

    reward_programs = accounts[4:6]

    with reverts("INVALID_LENGTH"):
        top_up_reward_program_easy_track_executor.beforeCreateMotionGuard(
            owner,
            encode_single(
                "(address[],uint256[])",
                (
                    [reward_programs[0].address, reward_programs[1].address],
                    [2000, 3000, 4000],
                ),
            ),
            {"from": easy_tracks_registry},
        )


def test_before_create_motion_guard(
    owner,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must ends without error if reward address is allowed and caller is trusted address"
    top_up_reward_program_easy_track_executor.initialize(
        owner,
        owner,
    )

    reward_programs = accounts[4:6]

    for reward_program in reward_programs:
        top_up_reward_program_easy_track_executor.addRewardProgram(
            reward_program, {"from": owner}
        )

    top_up_reward_program_easy_track_executor.beforeCreateMotionGuard(
        owner,
        encode_single(
            "(address[],uint256[])",
            ([reward_programs[0].address, reward_programs[1].address], [512, 1024]),
        ),
        {"from": easy_tracks_registry},
    )


def test_before_cancel_motion_guard_caller_is_not_trusted_address(
    stranger,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error: 'ADDRESS_NOT_TRUSTED'"
    with reverts("ADDRESS_NOT_TRUSTED"):
        top_up_reward_program_easy_track_executor.beforeCancelMotionGuard(
            stranger, "0x", "0x", {"from": easy_tracks_registry}
        )


def test_before_cancel_motion_guard(
    owner,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must ends without error if caller is trusted address"
    top_up_reward_program_easy_track_executor.beforeCancelMotionGuard(
        owner, "0x", "0x", {"from": easy_tracks_registry}
    )


def test_execute_reward_program_not_found(
    owner,
    stranger,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must fail with error 'REWARD_PROGRAM_NOT_FOUND' error"

    top_up_reward_program_easy_track_executor.initialize(
        owner,
        owner,
    )
    reward_programs = accounts[5:7]

    top_up_reward_program_easy_track_executor.addRewardProgram(
        reward_programs[1], {"from": owner}
    )

    motion_data = encode_single(
        "(address[],uint256[])",
        [[reward_programs[0].address, reward_programs[1].address], [1000, 2000]],
    )

    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        top_up_reward_program_easy_track_executor.execute(
            motion_data, "0x", {"from": easy_tracks_registry}
        )


def test_execute_reward_program(
    owner,
    finance,
    stranger,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    "Must return correct evm script if all reward program addresses is allowed"

    top_up_reward_program_easy_track_executor.initialize(
        owner,
        owner,
    )
    reward_programs = accounts[5:7]

    for reward_program in reward_programs:
        top_up_reward_program_easy_track_executor.addRewardProgram(
            reward_program, {"from": owner}
        )

    motion_data = encode_single(
        "(address[],uint256[])",
        [[reward_programs[0].address, reward_programs[1].address], [1000, 2000]],
    )

    evm_script = top_up_reward_program_easy_track_executor.execute.call(
        motion_data, "0x", {"from": easy_tracks_registry}
    )

    expected_script = encode_call_script(
        [
            (
                constants.FINANCE,
                finance.newImmediatePayment.encode_input(
                    constants.LDO_TOKEN,
                    reward_programs[0],
                    1000,
                    "Reward program top up",
                ),
            ),
            (
                constants.FINANCE,
                finance.newImmediatePayment.encode_input(
                    constants.LDO_TOKEN,
                    reward_programs[1],
                    2000,
                    "Reward program top up",
                ),
            ),
        ]
    )

    assert evm_script == expected_script
