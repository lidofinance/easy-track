from eth_abi import encode
from brownie import reverts
from utils.evm_script import encode_call_script

REWARD_PROGRAM_ADDRESS = "0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF"
REWARD_PROGRAM_TITLE = "New Reward Program"
EVM_SCRIPT_CALLDATA = (
    "0x"
    + encode(
        ["address","string"], [REWARD_PROGRAM_ADDRESS, REWARD_PROGRAM_TITLE]
    ).hex()
)


def test_deploy(owner, reward_programs_registry, AddRewardProgram):
    "Must deploy contract with correct data"
    contract = owner.deploy(AddRewardProgram, owner, reward_programs_registry)
    assert contract.trustedCaller() == owner
    assert contract.rewardProgramsRegistry() == reward_programs_registry


def test_create_evm_script_called_by_stranger(stranger, add_reward_program):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        add_reward_program.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_create_evm_script_reward_program_already_added(
    owner, add_reward_program, reward_programs_registry, evm_script_executor_stub
):
    "Must revert with message 'REWARD_PROGRAM_ALREADY_ADDED'"
    "if reward program already listed in RewardProgramsRegistry"
    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESS, REWARD_PROGRAM_TITLE, {"from": evm_script_executor_stub}
    )
    assert reward_programs_registry.isRewardProgram(REWARD_PROGRAM_ADDRESS)

    with reverts("REWARD_PROGRAM_ALREADY_ADDED"):
        add_reward_program.createEVMScript(
            owner,
            EVM_SCRIPT_CALLDATA,
        )


def test_create_evm_script(owner, add_reward_program, reward_programs_registry):
    "Must create correct EVMScript if all requirements are met"
    evm_script = add_reward_program.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [
            (
                reward_programs_registry.address,
                reward_programs_registry.addRewardProgram.encode_input(
                    REWARD_PROGRAM_ADDRESS, REWARD_PROGRAM_TITLE
                ),
            )
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(add_reward_program):
    "Must decode EVMScript call data correctly"
    assert add_reward_program.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == (
        REWARD_PROGRAM_ADDRESS,
        REWARD_PROGRAM_TITLE,
    )
