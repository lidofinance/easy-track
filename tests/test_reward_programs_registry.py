from brownie import reverts
from utils.test_helpers import access_control_revert_message


def test_deploy(owner, voting, evm_script_executor_stub, RewardProgramsRegistry):
    "Must deploy contract with correct trustedCaller address"
    contract = owner.deploy(
        RewardProgramsRegistry,
        voting,
        [voting, evm_script_executor_stub],
        [voting, evm_script_executor_stub],
    )
    # Voting must be admin of the RewardProgramsRegistry
    assert contract.hasRole(contract.DEFAULT_ADMIN_ROLE(), voting)

    # Voting must have rights to add/remove reward programs
    assert contract.hasRole(contract.ADD_REWARD_PROGRAM_ROLE(), voting)
    assert contract.hasRole(contract.REMOVE_REWARD_PROGRAM_ROLE(), voting)

    # EVMScriptExecutor must have rights to add/remove reward programs
    assert contract.hasRole(
        contract.ADD_REWARD_PROGRAM_ROLE(), evm_script_executor_stub
    )
    assert contract.hasRole(
        contract.REMOVE_REWARD_PROGRAM_ROLE(), evm_script_executor_stub
    )


def test_add_reward_program_called_by_stranger(stranger, reward_programs_registry):
    "Must revert with correct Access Control message if called by address without role 'ADD_REWARD_PROGRAM_ROLE'"
    assert not reward_programs_registry.hasRole(
        reward_programs_registry.ADD_REWARD_PROGRAM_ROLE(), stranger
    )
    with reverts(
        access_control_revert_message(
            stranger, reward_programs_registry.ADD_REWARD_PROGRAM_ROLE()
        )
    ):
        reward_programs_registry.addRewardProgram(stranger, "", {"from": stranger})


def test_add_reward_program(
    evm_script_executor_stub, stranger, reward_programs_registry
):
    "Must add new reward program to rewardPrograms array and emit RewardProgramAdded(_rewardProgram, _title) event."
    "When called with already added reward program fails with error 'REWARD_PROGRAM_ALREADY_ADDED' error"
    new_reward_program = stranger
    tx = reward_programs_registry.addRewardProgram(
        new_reward_program, "Reward Program", {"from": evm_script_executor_stub}
    )
    # validate events
    assert len(tx.events) == 1
    assert tx.events["RewardProgramAdded"]["_rewardProgram"] == new_reward_program
    assert tx.events["RewardProgramAdded"]["_title"] == "Reward Program"

    # validate that reward program was added
    reward_programs = reward_programs_registry.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == new_reward_program

    # fails when reward program adds second time
    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        reward_programs_registry.addRewardProgram(
            new_reward_program, "Reward Program", {"from": evm_script_executor_stub}
        )


def test_remove_reward_program_called_by_stranger(
    owner, stranger, reward_programs_registry
):
    "Must revert with correct Access Control message if called by address without role 'REMOVE_REWARD_PROGRAM_ROLE'"
    assert not reward_programs_registry.hasRole(
        reward_programs_registry.REMOVE_REWARD_PROGRAM_ROLE(), stranger
    )
    with reverts(
        access_control_revert_message(
            stranger, reward_programs_registry.REMOVE_REWARD_PROGRAM_ROLE()
        )
    ):
        reward_programs_registry.removeRewardProgram(stranger, {"from": stranger})


def test_remove_reward_program_with_not_existed_reward_program(
    stranger, reward_programs_registry, evm_script_executor_stub
):
    "Must revert with message 'REWARD_PROGRAM_NOT_FOUND' error"
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        reward_programs_registry.removeRewardProgram(
            stranger, {"from": evm_script_executor_stub}
        )


def test_remove_reward_program(
    accounts, reward_programs_registry, evm_script_executor_stub
):
    "Must remove reward program from the list of allowed programs and emit RewardProgramRemoved(_rewardProgram) event"
    reward_programs = accounts[4:9]

    for reward_program in reward_programs:
        reward_programs_registry.addRewardProgram(
            reward_program, "", {"from": evm_script_executor_stub}
        )

    # sets the order in which reward_programs will be removed
    removing_order = [2, 3, 1, 0, 0]

    # while len(reward_programs) > 0:
    for index in removing_order:
        reward_program = reward_programs.pop(index)

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
