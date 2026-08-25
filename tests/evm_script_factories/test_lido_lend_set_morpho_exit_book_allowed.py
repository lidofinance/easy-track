import pytest
from brownie import LidoLendExitBookActions, MorphoExitBookStub, ZERO_ADDRESS, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script
from utils.lido_lend import MARKET_PARAMS_ABI_TYPE

MARKET_PARAMS = (
    f"0x{1:040x}",
    f"0x{2:040x}",
    f"0x{3:040x}",
    f"0x{4:040x}",
    800000000000000000,
)
SECOND_MARKET_PARAMS = (
    f"0x{5:040x}",
    f"0x{6:040x}",
    f"0x{7:040x}",
    f"0x{8:040x}",
    900000000000000000,
)
SET_MORPHO_EXIT_BOOK_ALLOWED = 0


def payload(exit_book, market_params, allowed):
    return encode(
        ["address", f"{MARKET_PARAMS_ABI_TYPE}[]", "bool"],
        [str(exit_book), market_params, allowed],
    )


def calldata(exit_book, market_params, allowed):
    return (
        "0x"
        + encode(
            ["uint8", "bytes"],
            [SET_MORPHO_EXIT_BOOK_ALLOWED, payload(exit_book, market_params, allowed)],
        ).hex()
    )


@pytest.fixture(scope="module")
def morpho_exit_book(owner):
    return MorphoExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner):
    return LidoLendExitBookActions.deploy(owner, {"from": owner})


def test_create_evm_script_called_by_stranger(stranger, morpho_exit_book, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata(morpho_exit_book, [MARKET_PARAMS], True))


def test_create_evm_script_zero_exit_book(owner, factory):
    with reverts("ZERO_EXIT_BOOK"):
        factory.createEVMScript(owner, calldata(ZERO_ADDRESS, [MARKET_PARAMS], True))


def test_create_evm_script_empty_markets(owner, morpho_exit_book, factory):
    with reverts("EMPTY_MARKETS_LIST"):
        factory.createEVMScript(owner, calldata(morpho_exit_book, [], True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, morpho_exit_book, factory, allowed):
    assert factory.createEVMScript(
        owner, calldata(morpho_exit_book, [MARKET_PARAMS, SECOND_MARKET_PARAMS], allowed)
    ) == encode_call_script(
        [
            (morpho_exit_book.address, morpho_exit_book.setMarketAllowed.encode_input(MARKET_PARAMS, allowed)),
            (
                morpho_exit_book.address,
                morpho_exit_book.setMarketAllowed.encode_input(SECOND_MARKET_PARAMS, allowed),
            ),
        ]
    )


def test_decode_evm_script_call_data(factory, morpho_exit_book):
    action, encoded_payload = factory.decodeEVMScriptCallData(
        calldata(morpho_exit_book, [MARKET_PARAMS, SECOND_MARKET_PARAMS], True)
    )
    assert action == SET_MORPHO_EXIT_BOOK_ALLOWED
    exit_book, market_params, allowed = factory.decodeSetMorphoExitBookAllowedPayload(encoded_payload)
    assert exit_book == morpho_exit_book
    assert market_params == [MARKET_PARAMS, SECOND_MARKET_PARAMS]
    assert allowed is True


def test_rejects_unknown_action(owner, factory):
    encoded = "0x" + encode(["uint8", "bytes"], [255, b""]).hex()
    with reverts():
        factory.createEVMScript(owner, encoded)


def test_permissions_reject_exit_book_not_registered(
    owner,
    stranger,
    morpho_exit_book,
    factory,
    EVMScriptPermissionsWrapper,
):
    permission = morpho_exit_book.address + morpho_exit_book.setMarketAllowed.signature[2:]
    evm_script = factory.createEVMScript(owner, calldata(stranger, [MARKET_PARAMS], True))
    permissions = EVMScriptPermissionsWrapper.deploy({"from": owner})

    assert not permissions.canExecuteEVMScript(permission, evm_script)
