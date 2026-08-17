import pytest
from brownie import Erc4626ExitBookStub, LidoLendSetErc4626ExitBookAllowed, ZERO_ADDRESS, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

VAULT = f"0x{1:040x}"
SECOND_VAULT = f"0x{2:040x}"


def calldata(vaults, allowed):
    return "0x" + encode(["address[]", "bool"], [vaults, allowed]).hex()


@pytest.fixture(scope="module")
def erc4626_exit_book(owner):
    return Erc4626ExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner, erc4626_exit_book):
    return LidoLendSetErc4626ExitBookAllowed.deploy(owner, erc4626_exit_book, {"from": owner})


def test_deploy(owner, erc4626_exit_book, factory):
    assert factory.trustedCaller() == owner
    assert factory.erc4626ExitBook() == erc4626_exit_book


def test_create_evm_script_called_by_stranger(stranger, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata([VAULT], True))


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
    vaults, allowed = factory.decodeEVMScriptCallData(calldata([VAULT, SECOND_VAULT], True))
    assert vaults == [VAULT, SECOND_VAULT]
    assert allowed is True
