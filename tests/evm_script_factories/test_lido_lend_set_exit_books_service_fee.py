import pytest
from brownie import (
    Erc4626ExitBookStub,
    LidoLendSetExitBooksServiceFee,
    MorphoExitBookStub,
    ZERO_ADDRESS,
    reverts,
)
from eth_abi import encode

from utils.evm_script import encode_call_script


FEE_RECIPIENT = f"0x{1:040x}"
SERVICE_FEE = 10**17
MAX_SERVICE_FEE = 25 * 10**16


def calldata(exit_books, fee_recipient=FEE_RECIPIENT, service_fee=SERVICE_FEE):
    return (
        "0x"
        + encode(
            ["address[]", "address", "uint256"],
            [exit_books, fee_recipient, service_fee],
        ).hex()
    )


@pytest.fixture(scope="module")
def exit_books(owner):
    return (
        MorphoExitBookStub.deploy({"from": owner}),
        Erc4626ExitBookStub.deploy({"from": owner}),
    )


@pytest.fixture(scope="module")
def factory(owner):
    return LidoLendSetExitBooksServiceFee.deploy(owner, {"from": owner})


def test_deploy(owner, factory):
    assert factory.trustedCaller() == owner


def test_create_evm_script_called_by_stranger(stranger, exit_books, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata([book.address for book in exit_books]))


def test_create_evm_script_empty_exit_books(owner, factory):
    with reverts("EMPTY_EXIT_BOOKS"):
        factory.createEVMScript(owner, calldata([]))


def test_create_evm_script_zero_exit_book(owner, exit_books, factory):
    with reverts("ZERO_EXIT_BOOK"):
        factory.createEVMScript(owner, calldata([exit_books[0].address, ZERO_ADDRESS]))


def test_create_evm_script_accepts_exit_book_not_known_at_deployment(owner, stranger, exit_books, factory):
    books = [exit_books[0].address, stranger.address]
    assert factory.createEVMScript(owner, calldata(books)) == encode_call_script(
        [(book, exit_books[0].setServiceFee.encode_input(FEE_RECIPIENT, SERVICE_FEE)) for book in books]
    )


def test_permissions_reject_exit_book_not_registered(
    owner,
    stranger,
    exit_books,
    factory,
    EVMScriptPermissionsWrapper,
):
    permission = exit_books[0].address + exit_books[0].setServiceFee.signature[2:]
    evm_script = factory.createEVMScript(
        owner,
        calldata([exit_books[0].address, stranger.address]),
    )
    permissions = EVMScriptPermissionsWrapper.deploy({"from": owner})

    assert not permissions.canExecuteEVMScript(permission, evm_script)


def test_create_evm_script_fee_too_high(owner, exit_books, factory):
    with reverts("FEE_TOO_HIGH"):
        factory.createEVMScript(
            owner,
            calldata([book.address for book in exit_books], service_fee=MAX_SERVICE_FEE + 1),
        )


def test_create_evm_script_recipient_required(owner, exit_books, factory):
    with reverts("FEE_RECIPIENT_REQUIRED"):
        factory.createEVMScript(
            owner,
            calldata([book.address for book in exit_books], fee_recipient=ZERO_ADDRESS),
        )


def test_create_evm_script_allows_zero_recipient_for_zero_fee(owner, exit_books, factory):
    books = [book.address for book in exit_books]
    assert factory.createEVMScript(owner, calldata(books, ZERO_ADDRESS, 0)) == encode_call_script(
        [(book.address, book.setServiceFee.encode_input(ZERO_ADDRESS, 0)) for book in exit_books]
    )


def test_create_evm_script_preserves_exit_book_order(owner, exit_books, factory):
    books = [book.address for book in reversed(exit_books)]
    assert factory.createEVMScript(owner, calldata(books)) == encode_call_script(
        [(book.address, book.setServiceFee.encode_input(FEE_RECIPIENT, SERVICE_FEE)) for book in reversed(exit_books)]
    )


def test_decode_evm_script_call_data(exit_books, factory):
    books = [book.address for book in exit_books]
    assert factory.decodeEVMScriptCallData(calldata(books)) == (books, FEE_RECIPIENT, SERVICE_FEE)
