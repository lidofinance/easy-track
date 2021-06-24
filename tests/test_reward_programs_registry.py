import random

from eth_abi import encode_single
from brownie import RewardProgramsRegistry, accounts, ZERO_ADDRESS, reverts

import constants
from utils.evm_script import encode_call_script


def test_deploy(owner, evm_script_executor_stub):
    "Must deploy contract with correct params"

    contract = owner.deploy(RewardProgramsRegistry, evm_script_executor_stub)

    assert contract.evmScriptExecutor() == evm_script_executor_stub


def test_add_reward_program_called_by_stranger(
    owner, stranger, reward_programs_registry
):
    "Must fail with error 'FORBIDDEN' error"
    with reverts("FORBIDDEN"):
        reward_programs_registry.addRewardProgram(stranger, {"from": stranger})


def test_add_reward_program(
    evm_script_executor_stub, stranger, reward_programs_registry
):
    "Must add new reward program to rewardPrograms array and fail with"
    "error 'REWARD_PROGRAM_ALREADY_ADDED' error on call with same reward program"
    reward_programs_registry.addRewardProgram(
        stranger, {"from": evm_script_executor_stub}
    )

    reward_programs = reward_programs_registry.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == stranger

    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        reward_programs_registry.addRewardProgram(
            stranger, {"from": evm_script_executor_stub}
        )


def test_remove_reward_program_called_by_stranger(
    owner, stranger, reward_programs_registry
):
    "Must fail with error 'FORBIDDEN' error"
    with reverts("FORBIDDEN"):
        reward_programs_registry.removeRewardProgram(stranger, {"from": stranger})


def test_remove_reward_program_with_not_existed_reward_program(
    stranger, reward_programs_registry, evm_script_executor_stub
):
    "Must fail with error 'REWARD_PROGRAM_NOT_FOUND' error"
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        reward_programs_registry.removeRewardProgram(
            stranger, {"from": evm_script_executor_stub}
        )


def test_remove_reward_program(reward_programs_registry, evm_script_executor_stub):
    "Must remove reward program from the list of allowed programs"
    reward_programs = accounts[4:9]

    for reward_program in reward_programs:
        reward_programs_registry.addRewardProgram(
            reward_program, {"from": evm_script_executor_stub}
        )

    while len(reward_programs) > 0:
        index_to_delete = random.randint(0, len(reward_programs) - 1)
        reward_program = reward_programs.pop(index_to_delete)

        assert reward_programs_registry.isRewardProgram(reward_program)
        reward_programs_registry.removeRewardProgram(
            reward_program, {"from": evm_script_executor_stub}
        )
        assert not reward_programs_registry.isRewardProgram(reward_program)

        contract_reward_programs = reward_programs_registry.getRewardPrograms()
        assert len(reward_programs) == len(contract_reward_programs)
        # validate that was deleted correct address by join
        # test set with resulting set their size must be same
        assert len(set(reward_programs).union(contract_reward_programs)) == len(
            contract_reward_programs
        )
