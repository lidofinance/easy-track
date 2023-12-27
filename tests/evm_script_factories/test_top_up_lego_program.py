import pytest
import brownie
from brownie import reverts
from eth_abi import encode_single

from utils.evm_script import encode_call_script
from utils.lido import addresses

REWARD_AMOUNTS = [10 ** 18, 2 * 10 ** 18]

@pytest.fixture(scope="module")
def reward_token_addresses():
    lido_addresses = addresses(network=brownie.network.show_active())
    return [lido_addresses.ldo, lido_addresses.steth]



def test_deploy(owner, finance, lego_program, TopUpLegoProgram):
    "Must deploy contract with correct data"
    contract = owner.deploy(TopUpLegoProgram, owner, finance, lego_program)
    assert contract.trustedCaller() == owner
    assert contract.finance() == finance
    assert contract.legoProgram() == lego_program


def test_create_evm_script_called_by_stranger(stranger, top_up_lego_program):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        top_up_lego_program.createEVMScript(
            stranger, encode_call_data([], []), {"from": stranger}
        )


def test_create_evm_script_data_length_mismatch(owner, top_up_lego_program, reward_token_addresses):
    "Must revert with message 'LENGTH_MISMATCH' if rewardTokens and amounts has different lengths"
    with reverts("LENGTH_MISMATCH"):
        top_up_lego_program.createEVMScript(
            owner,
            encode_call_data(reward_token_addresses, [1 ** 18]),
        )


def test_create_evm_script_empty_data(owner, top_up_lego_program):
    "Must revert with message 'EMPTY_DATA' if called with empty lists"
    with reverts("EMPTY_DATA"):
        top_up_lego_program.createEVMScript(owner, encode_call_data([], []))


def test_create_evm_script_zero_amount(owner, top_up_lego_program, reward_token_addresses):
    "Must revert with message 'ZERO_AMOUNT' if some value in amounts has zero value"
    amounts = [1 ** 18, 0]

    with reverts("ZERO_AMOUNT"):
        top_up_lego_program.createEVMScript(
            owner, encode_call_data(reward_token_addresses, amounts)
        )


def test_create_evm_script(owner, lego_program, top_up_lego_program, finance, ldo, reward_token_addresses):
    "Must create correct EVMScript if all requirements are met"
    evm_script = top_up_lego_program.createEVMScript(
        owner, encode_call_data(reward_token_addresses, REWARD_AMOUNTS)
    )

    expected_evm_script = encode_call_script(
        [
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    reward_token_addresses[0],
                    lego_program,
                    REWARD_AMOUNTS[0],
                    "Lego Program Transfer",
                ),
            ),
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    reward_token_addresses[1],
                    lego_program,
                    REWARD_AMOUNTS[1],
                    "Lego Program Transfer",
                ),
            ),
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(top_up_lego_program, reward_token_addresses):
    "Must decode EVMScript call data correctly"
    assert top_up_lego_program.decodeEVMScriptCallData(
        encode_call_data(reward_token_addresses, REWARD_AMOUNTS)
    ) == (reward_token_addresses, REWARD_AMOUNTS)


def encode_call_data(addresses, amounts):
    return "0x" + encode_single("(address[],uint256[])", [addresses, amounts]).hex()
