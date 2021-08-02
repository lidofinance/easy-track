import random

from eth_abi import encode_single
from brownie import TopUpRewardPrograms, accounts, ZERO_ADDRESS, reverts

from utils.evm_script import encode_call_script

REWARD_PROGRAM_ADDRESSES = [
    "0xffffFfFffffFfffffFFfFfFFfFffFfFfFFFfFfaA",
    "0xfFFFfFfFfffFffFfFfFFfFFfffFfFfFffffffFbb",
]
REWARD_PROGRAM_AMOUNTS = [10 ** 18, 2 * 10 ** 18]


def test_deploy(owner, reward_programs_registry, finance, ldo):
    "Must deploy contract with correct data"
    contract = owner.deploy(
        TopUpRewardPrograms, owner, reward_programs_registry, finance, ldo
    )
    assert contract.trustedCaller() == owner
    assert contract.finance() == finance
    assert contract.rewardToken() == ldo
    assert contract.rewardProgramsRegistry() == reward_programs_registry


def test_create_evm_script_called_by_stranger(stranger, top_up_reward_programs):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        top_up_reward_programs.createEVMScript(
            stranger, encode_call_data([], []), {"from": stranger}
        )


def test_create_evm_script_data_length_mismatch(owner, top_up_reward_programs):
    "Must revert with message 'LENGTH_MISMATCH' if rewardPrograms and amounts has different lengths"
    with reverts("LENGTH_MISMATCH"):
        top_up_reward_programs.createEVMScript(
            owner,
            encode_call_data(REWARD_PROGRAM_ADDRESSES, [1 ** 18]),
        )


def test_create_evm_script_empty_data(owner, top_up_reward_programs):
    "Must revert with message 'EMPTY_DATA' if called with empty lists"
    with reverts("EMPTY_DATA"):
        top_up_reward_programs.createEVMScript(owner, encode_call_data([], []))


def test_create_evm_script_zero_amount(
    owner, top_up_reward_programs, reward_programs_registry, evm_script_executor_stub
):
    "Must revert with message 'ZERO_AMOUNT' if some value in amounts has zero value"
    amounts = [1 ** 18, 0]
    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESSES[0], "", {"from": evm_script_executor_stub}
    )
    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESSES[1], "", {"from": evm_script_executor_stub}
    )
    with reverts("ZERO_AMOUNT"):
        top_up_reward_programs.createEVMScript(
            owner, encode_call_data(REWARD_PROGRAM_ADDRESSES, amounts)
        )


def test_create_evm_script_reward_program_not_allowed(
    owner, top_up_reward_programs, reward_programs_registry, evm_script_executor_stub
):
    "Must revert with message 'REWARD_PROGRAM_NOT_ALLOWED' if passed"
    "reward program isn't listed in RewardProgramsRegistry"

    not_allowed_reward_program = accounts[3].address

    # empty reward programs edge case
    with reverts("REWARD_PROGRAM_NOT_ALLOWED"):
        top_up_reward_programs.createEVMScript(
            owner, encode_call_data(REWARD_PROGRAM_ADDRESSES, REWARD_PROGRAM_AMOUNTS)
        )

    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESSES[0], "", {"from": evm_script_executor_stub}
    )
    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESSES[1], "", {"from": evm_script_executor_stub}
    )

    # case with added reward programs
    with reverts("REWARD_PROGRAM_NOT_ALLOWED"):
        top_up_reward_programs.createEVMScript(
            owner,
            encode_call_data(
                [
                    REWARD_PROGRAM_ADDRESSES[0],
                    REWARD_PROGRAM_ADDRESSES[1],
                    not_allowed_reward_program,
                ],
                [REWARD_PROGRAM_AMOUNTS[0], REWARD_PROGRAM_AMOUNTS[1], 3 * 10 ** 18],
            ),
        )


def test_create_evm_script(
    owner,
    top_up_reward_programs,
    reward_programs_registry,
    evm_script_executor_stub,
    finance,
    ldo,
):
    "Must create correct EVMScript if all requirements are met"
    # add reward programs
    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESSES[0], "", {"from": evm_script_executor_stub}
    )
    reward_programs_registry.addRewardProgram(
        REWARD_PROGRAM_ADDRESSES[1], "", {"from": evm_script_executor_stub}
    )

    evm_script = top_up_reward_programs.createEVMScript(
        owner, encode_call_data(REWARD_PROGRAM_ADDRESSES, REWARD_PROGRAM_AMOUNTS)
    )

    expected_evm_script = encode_call_script(
        [
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    ldo,
                    REWARD_PROGRAM_ADDRESSES[0],
                    REWARD_PROGRAM_AMOUNTS[0],
                    "Reward program top up",
                ),
            ),
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    ldo,
                    REWARD_PROGRAM_ADDRESSES[1],
                    REWARD_PROGRAM_AMOUNTS[1],
                    "Reward program top up",
                ),
            ),
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(top_up_reward_programs):
    "Must decode EVMScript call data correctly"
    assert top_up_reward_programs.decodeEVMScriptCallData(
        encode_call_data(REWARD_PROGRAM_ADDRESSES, REWARD_PROGRAM_AMOUNTS)
    ) == (REWARD_PROGRAM_ADDRESSES, REWARD_PROGRAM_AMOUNTS)


def encode_call_data(addresses, amounts):
    return "0x" + encode_single("(address[],uint256[])", [addresses, amounts]).hex()
