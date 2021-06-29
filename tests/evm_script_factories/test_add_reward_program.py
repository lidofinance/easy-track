import random

from eth_abi import encode_single
from brownie import AddRewardProgram, reverts

from utils.evm_script import encode_call_script

REWARD_PROGRAM_ADDRESS = "0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF"
EVM_SCRIPT_CALL_DATA = "0x" + encode_single("(address)", [REWARD_PROGRAM_ADDRESS]).hex()


def test_deploy(owner, reward_programs_registry):
    "Must deploy contract with correct params"

    contract = owner.deploy(AddRewardProgram, owner, reward_programs_registry)

    assert contract.trustedCaller() == owner
    assert contract.rewardProgramsRegistry() == reward_programs_registry


def test_create_evm_script_called_by_stranger(stranger, add_reward_program):
    "Must fail with error 'CALLER_IS_FORBIDDEN'"
    with reverts("CALLER_IS_FORBIDDEN"):
        add_reward_program.createEVMScript(stranger, EVM_SCRIPT_CALL_DATA)


def test_create_evm_script_reward_program_already_added(
    owner, add_reward_program, reward_programs_registry, evm_script_executor_stub
):
    "Must fail with error 'REWARD_PROGRAM_ALREADY_ADDED'"

    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESS, {"from": evm_script_executor_stub}
    )
    assert reward_programs_registry.isRewardProgram(REWARD_PROGRAM_ADDRESS)

    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        add_reward_program.createEVMScript(
            owner,
            EVM_SCRIPT_CALL_DATA,
        )


def test_create_evm_script(owner, add_reward_program, reward_programs_registry):
    "Must create correct evm script"

    evm_script = add_reward_program.createEVMScript(owner, EVM_SCRIPT_CALL_DATA)
    expected_evm_script = encode_call_script(
        [
            (
                reward_programs_registry.address,
                reward_programs_registry.addRewardProgram.encode_input(
                    REWARD_PROGRAM_ADDRESS
                ),
            )
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(add_reward_program):
    assert (
        add_reward_program.decodeEVMScriptCallData(EVM_SCRIPT_CALL_DATA)
        == REWARD_PROGRAM_ADDRESS
    )
