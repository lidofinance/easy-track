import pytest
from brownie import Erc4626ExitBookStub, LidoLendExitBookActions, ZERO_ADDRESS, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

VAULT = f"0x{1:040x}"
SECOND_VAULT = f"0x{2:040x}"
SET_ERC4626_EXIT_BOOK_ALLOWED = 1


def payload(exit_book, vaults, allowed):
    return encode(["address", "address[]", "bool"], [str(exit_book), vaults, allowed])


def calldata(exit_book, vaults, allowed):
    return (
        "0x"
        + encode(
            ["uint8", "bytes"],
            [SET_ERC4626_EXIT_BOOK_ALLOWED, payload(exit_book, vaults, allowed)],
        ).hex()
    )


@pytest.fixture(scope="module")
def erc4626_exit_book(owner):
    return Erc4626ExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner):
    return LidoLendExitBookActions.deploy(owner, {"from": owner})


def test_create_evm_script_zero_exit_book(owner, factory):
    with reverts("ZERO_EXIT_BOOK"):
        factory.createEVMScript(owner, calldata(ZERO_ADDRESS, [VAULT], True))


def test_create_evm_script_empty_vaults(owner, erc4626_exit_book, factory):
    with reverts("EMPTY_VAULTS"):
        factory.createEVMScript(owner, calldata(erc4626_exit_book, [], True))


def test_create_evm_script_zero_vault(owner, erc4626_exit_book, factory):
    with reverts("ZERO_VAULT"):
        factory.createEVMScript(owner, calldata(erc4626_exit_book, [VAULT, ZERO_ADDRESS], True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, erc4626_exit_book, factory, allowed):
    assert factory.createEVMScript(
        owner, calldata(erc4626_exit_book, [VAULT, SECOND_VAULT], allowed)
    ) == encode_call_script(
        [
            (erc4626_exit_book.address, erc4626_exit_book.setVaultAllowed.encode_input(VAULT, allowed)),
            (erc4626_exit_book.address, erc4626_exit_book.setVaultAllowed.encode_input(SECOND_VAULT, allowed)),
        ]
    )


def test_decode_evm_script_call_data(factory, erc4626_exit_book):
    action, encoded_payload = factory.decodeEVMScriptCallData(calldata(erc4626_exit_book, [VAULT, SECOND_VAULT], True))
    assert action == SET_ERC4626_EXIT_BOOK_ALLOWED
    exit_book, vaults, allowed = factory.decodeSetErc4626ExitBookAllowedPayload(encoded_payload)
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
    evm_script = factory.createEVMScript(owner, calldata(stranger, [VAULT], True))
    permissions = EVMScriptPermissionsWrapper.deploy({"from": owner})

    assert not permissions.canExecuteEVMScript(permission, evm_script)
