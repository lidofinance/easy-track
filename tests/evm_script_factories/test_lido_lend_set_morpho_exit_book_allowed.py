import pytest
from brownie import LidoLendSetMorphoExitBookAllowed, MorphoExitBookStub, reverts
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


def calldata(allowed):
    return "0x" + encode([MARKET_PARAMS_ABI_TYPE, "bool"], [MARKET_PARAMS, allowed]).hex()


@pytest.fixture(scope="module")
def morpho_exit_book(owner):
    return MorphoExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner, morpho_exit_book):
    return LidoLendSetMorphoExitBookAllowed.deploy(owner, morpho_exit_book, {"from": owner})


def test_deploy(owner, morpho_exit_book, factory):
    assert factory.trustedCaller() == owner
    assert factory.morphoExitBook() == morpho_exit_book


def test_create_evm_script_called_by_stranger(stranger, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata(True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, morpho_exit_book, factory, allowed):
    assert factory.createEVMScript(owner, calldata(allowed)) == encode_call_script(
        [(morpho_exit_book.address, morpho_exit_book.setMarketAllowed.encode_input(MARKET_PARAMS, allowed))]
    )


def test_decode_evm_script_call_data(factory):
    market_params, allowed = factory.decodeEVMScriptCallData(calldata(True))
    assert market_params == MARKET_PARAMS
    assert allowed is True
