import pytest
from brownie import Erc4626ExitBookStub, LidoLendSetErc4626ExitBookAllowed, ZERO_ADDRESS, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

VAULT = f"0x{1:040x}"
SECOND_VAULT = f"0x{2:040x}"


def calldata(exit_book, vaults, allowed):
    return "0x" + encode(["address", "address[]", "bool"], [exit_book, vaults, allowed]).hex()


@pytest.fixture(scope="module")
def erc4626_exit_book(owner):
    return Erc4626ExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner):
    return LidoLendSetErc4626ExitBookAllowed.deploy(owner, {"from": owner})


def test_deploy(owner, factory):
    assert factory.trustedCaller() == owner


def test_create_evm_script_called_by_stranger(stranger, erc4626_exit_book, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata(erc4626_exit_book.address, [VAULT], True))


def test_create_evm_script_zero_exit_book(owner, factory):
    with reverts("ZERO_EXIT_BOOK"):
        factory.createEVMScript(owner, calldata(ZERO_ADDRESS, [VAULT], True))


def test_create_evm_script_empty_vaults(owner, erc4626_exit_book, factory):
    with reverts("EMPTY_VAULTS"):
        factory.createEVMScript(owner, calldata(erc4626_exit_book.address, [], True))


def test_create_evm_script_zero_vault(owner, erc4626_exit_book, factory):
    with reverts("ZERO_VAULT"):
        factory.createEVMScript(owner, calldata(erc4626_exit_book.address, [VAULT, ZERO_ADDRESS], True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, erc4626_exit_book, factory, allowed):
    assert factory.createEVMScript(
        owner,
        calldata(erc4626_exit_book.address, [VAULT, SECOND_VAULT], allowed),
    ) == encode_call_script(
        [
            (erc4626_exit_book.address, erc4626_exit_book.setVaultAllowed.encode_input(VAULT, allowed)),
            (erc4626_exit_book.address, erc4626_exit_book.setVaultAllowed.encode_input(SECOND_VAULT, allowed)),
        ]
    )


def test_decode_evm_script_call_data(factory, erc4626_exit_book):
    exit_book, vaults, allowed = factory.decodeEVMScriptCallData(
        calldata(erc4626_exit_book.address, [VAULT, SECOND_VAULT], True)
    )
    assert exit_book == erc4626_exit_book
    assert vaults == [VAULT, SECOND_VAULT]
    assert allowed is True


def test_permissions_reject_exit_book_not_registered(
    owner,
    stranger,
    erc4626_exit_book,
    factory,
    EVMScriptPermissionsWrapper,
):
    permission = erc4626_exit_book.address + erc4626_exit_book.setVaultAllowed.signature[2:]
    evm_script = factory.createEVMScript(owner, calldata(stranger.address, [VAULT], True))
    permissions = EVMScriptPermissionsWrapper.deploy({"from": owner})

    assert not permissions.canExecuteEVMScript(permission, evm_script)
