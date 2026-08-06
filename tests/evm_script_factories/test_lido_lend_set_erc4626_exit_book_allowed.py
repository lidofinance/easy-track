import pytest
from brownie import Erc4626ExitBookStub, LidoLendSetErc4626ExitBookAllowed, ZERO_ADDRESS, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

VAULT = f"0x{1:040x}"


def calldata(vault, allowed):
    return "0x" + encode(["address", "bool"], [vault, allowed]).hex()


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
        factory.createEVMScript(stranger, calldata(VAULT, True))


def test_create_evm_script_zero_vault(owner, factory):
    with reverts("ZERO_VAULT"):
        factory.createEVMScript(owner, calldata(ZERO_ADDRESS, True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, erc4626_exit_book, factory, allowed):
    assert factory.createEVMScript(owner, calldata(VAULT, allowed)) == encode_call_script(
        [(erc4626_exit_book.address, erc4626_exit_book.setVaultAllowed.encode_input(VAULT, allowed))]
    )


def test_decode_evm_script_call_data(factory):
    vault, allowed = factory.decodeEVMScriptCallData(calldata(VAULT, True))
    assert vault == VAULT
    assert allowed is True
