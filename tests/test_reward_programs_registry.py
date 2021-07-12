import random
from brownie import RewardProgramsRegistry, accounts, reverts


def test_deploy(owner, evm_script_executor_stub):
    "Must deploy contract with correct trustedCaller address"
    contract = owner.deploy(RewardProgramsRegistry, evm_script_executor_stub)
    assert contract.trustedCaller() == evm_script_executor_stub


def test_add_reward_program_called_by_stranger(
    owner, stranger, reward_programs_registry
):
    "Must fail with error 'FORBIDDEN' error"
    with reverts("CALLER_IS_FORBIDDEN"):
        reward_programs_registry.addRewardProgram(stranger, {"from": stranger})


def test_add_reward_program(
    evm_script_executor_stub, stranger, reward_programs_registry
):
    "Must add new reward program to rewardPrograms array and emit RewardProgramAdded(_rewardProgram) event."
    "When called with already added reward program fails with error 'REWARD_PROGRAM_ALREADY_ADDED' error"

    new_reward_program = stranger
    tx = reward_programs_registry.addRewardProgram(
        new_reward_program, {"from": evm_script_executor_stub}
    )
    # validate events
    assert len(tx.events) == 1
    assert tx.events["RewardProgramAdded"]["_rewardProgram"] == new_reward_program

    # validate that reward program was added
    reward_programs = reward_programs_registry.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == new_reward_program

    # fails when reward program adds second time
    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        reward_programs_registry.addRewardProgram(
            new_reward_program, {"from": evm_script_executor_stub}
        )


def test_remove_reward_program_called_by_stranger(
    owner, stranger, reward_programs_registry
):
    "Must fail with error 'FORBIDDEN' error"
    with reverts("CALLER_IS_FORBIDDEN"):
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
    "Must remove reward program from the list of allowed programs and emit RewardProgramRemoved(_rewardProgram) event"
    reward_programs = accounts[4:9]

    for reward_program in reward_programs:
        reward_programs_registry.addRewardProgram(
            reward_program, {"from": evm_script_executor_stub}
        )

    while len(reward_programs) > 0:
        index_to_delete = random.randint(0, len(reward_programs) - 1)
        reward_program = reward_programs.pop(index_to_delete)

        assert reward_programs_registry.isRewardProgram(reward_program)
        tx = reward_programs_registry.removeRewardProgram(
            reward_program, {"from": evm_script_executor_stub}
        )
        # validate events
        assert len(tx.events) == 1
        assert tx.events["RewardProgramRemoved"]["_rewardProgram"] == reward_program
        assert not reward_programs_registry.isRewardProgram(reward_program)

        contract_reward_programs = reward_programs_registry.getRewardPrograms()
        assert len(reward_programs) == len(contract_reward_programs)
        # validate that was deleted correct address by join
        # test set with resulting set their size must be same
        assert len(set(reward_programs).union(contract_reward_programs)) == len(
            contract_reward_programs
        )
