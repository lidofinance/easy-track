import pytest
from brownie import (
    Erc4626ExitBookStub,
    LidoLendCoreStub,
    LidoLendExitBookActions,
    MorphoExitBookStub,
    reverts,
    web3,
)
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
UNKNOWN_MARKET_PARAMS = (
    f"0x{9:040x}",
    f"0x{10:040x}",
    f"0x{11:040x}",
    f"0x{12:040x}",
    700000000000000000,
)
SET_MORPHO_EXIT_BOOK_ALLOWED = 0


def payload(market_params, allowed):
    return encode([f"{MARKET_PARAMS_ABI_TYPE}[]", "bool"], [market_params, allowed])


def calldata(market_params, allowed):
    return (
        "0x"
        + encode(
            ["uint8", "bytes"],
            [SET_MORPHO_EXIT_BOOK_ALLOWED, payload(market_params, allowed)],
        ).hex()
    )


@pytest.fixture(scope="module")
def core(owner):
    core = LidoLendCoreStub.deploy({"from": owner})
    for market_params in (MARKET_PARAMS, SECOND_MARKET_PARAMS):
        market_id = web3.keccak(encode([MARKET_PARAMS_ABI_TYPE], [market_params]))
        core.activateMarket(market_id, market_params, False, {"from": owner})
    return core


@pytest.fixture(scope="module")
def morpho_exit_book(owner, core):
    exit_book = MorphoExitBookStub.deploy({"from": owner})
    exit_book.setMorpho(core, {"from": owner})
    return exit_book


@pytest.fixture(scope="module")
def erc4626_exit_book(owner):
    return Erc4626ExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner, morpho_exit_book, erc4626_exit_book):
    return LidoLendExitBookActions.deploy(owner, morpho_exit_book, erc4626_exit_book, {"from": owner})


def test_create_evm_script_called_by_stranger(stranger, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata([MARKET_PARAMS], True))


def test_create_evm_script_empty_markets(owner, factory):
    with reverts("EMPTY_MARKETS_LIST"):
        factory.createEVMScript(owner, calldata([], True))


def test_create_evm_script_unknown_market(owner, factory):
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, calldata([UNKNOWN_MARKET_PARAMS], True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, morpho_exit_book, factory, allowed):
    assert factory.createEVMScript(
        owner, calldata([MARKET_PARAMS, SECOND_MARKET_PARAMS], allowed)
    ) == encode_call_script(
        [
            (morpho_exit_book.address, morpho_exit_book.setMarketAllowed.encode_input(MARKET_PARAMS, allowed)),
            (
                morpho_exit_book.address,
                morpho_exit_book.setMarketAllowed.encode_input(SECOND_MARKET_PARAMS, allowed),
            ),
        ]
    )


def test_decode_evm_script_call_data(factory):
    action, encoded_payload = factory.decodeEVMScriptCallData(calldata([MARKET_PARAMS, SECOND_MARKET_PARAMS], True))
    assert action == SET_MORPHO_EXIT_BOOK_ALLOWED
    market_params, allowed = factory.decodeSetMorphoExitBookAllowedPayload(encoded_payload)
    assert market_params == [MARKET_PARAMS, SECOND_MARKET_PARAMS]
    assert allowed is True


def test_rejects_unknown_action(owner, factory):
    encoded = "0x" + encode(["uint8", "bytes"], [255, b""]).hex()
    with reverts():
        factory.createEVMScript(owner, encoded)


def test_rejects_removed_service_fee_action(owner, factory):
    payload = encode(["address", "uint256"], [owner.address, 0])
    encoded = "0x" + encode(["uint8", "bytes"], [2, payload]).hex()
    with reverts():
        factory.createEVMScript(owner, encoded)
