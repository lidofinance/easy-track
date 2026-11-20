import pytest
from brownie import Erc4626ExitBookStub, LidoLendExitBookActions, MorphoExitBookStub, ZERO_ADDRESS, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

VAULT = f"0x{1:040x}"
SECOND_VAULT = f"0x{2:040x}"
SET_ERC4626_EXIT_BOOK_ALLOWED = 1


def payload(vaults, allowed):
    return encode(["address[]", "bool"], [vaults, allowed])


def calldata(vaults, allowed):
    return (
        "0x"
        + encode(
            ["uint8", "bytes"],
            [SET_ERC4626_EXIT_BOOK_ALLOWED, payload(vaults, allowed)],
        ).hex()
    )


@pytest.fixture(scope="module")
def erc4626_exit_book(owner):
    return Erc4626ExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def morpho_exit_book(owner):
    return MorphoExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner, morpho_exit_book, erc4626_exit_book):
    return LidoLendExitBookActions.deploy(owner, morpho_exit_book, erc4626_exit_book, {"from": owner})


def test_create_evm_script_empty_vaults(owner, factory):
    with reverts("EMPTY_VAULTS"):
        factory.createEVMScript(owner, calldata([], True))


def test_create_evm_script_zero_vault(owner, factory):
    with reverts("ZERO_VAULT"):
        factory.createEVMScript(owner, calldata([VAULT, ZERO_ADDRESS], True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, erc4626_exit_book, factory, allowed):
    assert factory.createEVMScript(owner, calldata([VAULT, SECOND_VAULT], allowed)) == encode_call_script(
        [
            (erc4626_exit_book.address, erc4626_exit_book.setVaultAllowed.encode_input(VAULT, allowed)),
            (erc4626_exit_book.address, erc4626_exit_book.setVaultAllowed.encode_input(SECOND_VAULT, allowed)),
        ]
    )


def test_decode_evm_script_call_data(factory):
    action, encoded_payload = factory.decodeEVMScriptCallData(calldata([VAULT, SECOND_VAULT], True))
    assert action == SET_ERC4626_EXIT_BOOK_ALLOWED
    vaults, allowed = factory.decodeSetErc4626ExitBookAllowedPayload(encoded_payload)
    assert vaults == [VAULT, SECOND_VAULT]
    assert allowed is True
