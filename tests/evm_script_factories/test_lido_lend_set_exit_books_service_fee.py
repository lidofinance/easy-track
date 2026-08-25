import pytest
from brownie import Erc4626ExitBookStub, LidoLendExitBookActions, MorphoExitBookStub, ZERO_ADDRESS, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

FEE_RECIPIENT = f"0x{1:040x}"
SERVICE_FEE = 10**17
MAX_SERVICE_FEE = 25 * 10**16
ACTION = 2


def calldata(exit_books, fee_recipient=FEE_RECIPIENT, service_fee=SERVICE_FEE):
    payload = encode(
        ["address[]", "address", "uint256"],
        [exit_books, fee_recipient, service_fee],
    )
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def exit_books(owner):
    return (
        MorphoExitBookStub.deploy({"from": owner}),
        Erc4626ExitBookStub.deploy({"from": owner}),
    )


@pytest.fixture(scope="module")
def factory(owner):
    return LidoLendExitBookActions.deploy(owner, {"from": owner})


def test_create_evm_script_empty_exit_books(owner, factory):
    with reverts("EMPTY_EXIT_BOOKS"):
        factory.createEVMScript(owner, calldata([]))


def test_create_evm_script_zero_exit_book(owner, exit_books, factory):
    with reverts("ZERO_EXIT_BOOK"):
        factory.createEVMScript(owner, calldata([exit_books[0].address, ZERO_ADDRESS]))


def test_create_evm_script_fee_too_high(owner, exit_books, factory):
    with reverts("FEE_TOO_HIGH"):
        factory.createEVMScript(
            owner,
            calldata([book.address for book in exit_books], service_fee=MAX_SERVICE_FEE + 1),
        )


def test_create_evm_script_recipient_required(owner, exit_books, factory):
    with reverts("FEE_RECIPIENT_REQUIRED"):
        factory.createEVMScript(owner, calldata([book.address for book in exit_books], fee_recipient=ZERO_ADDRESS))


@pytest.mark.parametrize(
    "fee_recipient,service_fee",
    [(FEE_RECIPIENT, SERVICE_FEE), (FEE_RECIPIENT, MAX_SERVICE_FEE), (ZERO_ADDRESS, 0)],
)
def test_create_evm_script_preserves_exit_book_order(
    owner,
    exit_books,
    factory,
    fee_recipient,
    service_fee,
):
    books = list(reversed(exit_books))
    assert factory.createEVMScript(
        owner, calldata([book.address for book in books], fee_recipient, service_fee)
    ) == encode_call_script(
        [(book.address, book.setServiceFee.encode_input(fee_recipient, service_fee)) for book in books]
    )


def test_permissions_reject_exit_book_not_registered(
    owner,
    stranger,
    exit_books,
    factory,
    EVMScriptPermissionsWrapper,
):
    permission = exit_books[0].address + exit_books[0].setServiceFee.signature[2:]
    evm_script = factory.createEVMScript(owner, calldata([exit_books[0].address, stranger.address]))
    permissions = EVMScriptPermissionsWrapper.deploy({"from": owner})

    assert not permissions.canExecuteEVMScript(permission, evm_script)


def test_decode_payload(exit_books, factory):
    action, payload = factory.decodeEVMScriptCallData(calldata([book.address for book in exit_books]))
    assert action == ACTION
    books, recipient, fee = factory.decodeSetServiceFeePayload(payload)
    assert books == [book.address for book in exit_books]
    assert recipient == FEE_RECIPIENT
    assert fee == SERVICE_FEE
