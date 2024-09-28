from eth_abi import encode
from brownie import reverts

from utils.evm_script import encode_call_script

REWARD_PROGRAM_ADDRESS = "0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF"
EVM_SCRIPT_CALLDATA = "0x" + encode(["address"], [REWARD_PROGRAM_ADDRESS]).hex()


def test_deploy(owner, reward_programs_registry, RemoveRewardProgram):
    "Must deploy contract with correct data"
    contract = owner.deploy(RemoveRewardProgram, owner, reward_programs_registry)
    assert contract.trustedCaller() == owner
    assert contract.rewardProgramsRegistry() == reward_programs_registry


def test_create_evm_script_called_by_stranger(stranger, remove_reward_program):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        remove_reward_program.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_create_evm_script_reward_program_already_added(
    owner, remove_reward_program, reward_programs_registry, evm_script_executor_stub
):
    "Must revert with message 'REWARD_PROGRAM_NOT_FOUND'"
    with reverts("REWARD_PROGRAM_NOT_FOUND"):
        remove_reward_program.createEVMScript(
            owner,
            EVM_SCRIPT_CALLDATA,
        )


def test_create_evm_script(owner, remove_reward_program, reward_programs_registry, evm_script_executor_stub):
    "Must create correct EVMScript if all requirements are met"
    reward_programs_registry.addRewardProgram(REWARD_PROGRAM_ADDRESS, "", {"from": evm_script_executor_stub})
    evm_script = remove_reward_program.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [
            (
                reward_programs_registry.address,
                reward_programs_registry.removeRewardProgram.encode_input(REWARD_PROGRAM_ADDRESS),
            )
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(remove_reward_program):
    "Must decode EVMScript call data correctly"
    assert remove_reward_program.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == REWARD_PROGRAM_ADDRESS
