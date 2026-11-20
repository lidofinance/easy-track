import pytest
from brownie import LidoLendCoreStub, LidoLendMarketManagerActions, LidoLendOwnerStub, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
NEW_FEE = 10**17
MAX_FEE = 25 * 10**16
ACTION = 5


def create_calldata(market_id, new_fee):
    payload = encode(["bytes32", "uint256"], [market_id, new_fee])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def market_params(owner, stranger):
    return (owner.address, stranger.address, owner.address, stranger.address, 8 * 10**17)


@pytest.fixture(scope="module")
def core_stub(owner, market_params):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.activateMarket(MARKET_ID, market_params, False, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    core_stub.setOwner(facade, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendMarketManagerActions.deploy(owner, owner_facade, {"from": owner})


def test_create_evm_script_market_not_found(owner, factory):
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_FEE))


def test_create_evm_script_fee_already_set(owner, factory):
    with reverts("FEE_ALREADY_SET"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, 0))


def test_create_evm_script_max_fee(owner, factory):
    with reverts("MAX_FEE_EXCEEDED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, MAX_FEE + 1))


@pytest.mark.parametrize("new_fee", [NEW_FEE, MAX_FEE])
def test_create_evm_script_creates_single_set_fee_call(owner, owner_facade, market_params, factory, new_fee):
    assert factory.createEVMScript(owner, create_calldata(MARKET_ID, new_fee)) == encode_call_script(
        [(owner_facade.address, owner_facade.setFee.encode_input(market_params, new_fee))]
    )


def test_decode_payload(factory):
    action, payload = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_FEE))
    assert action == ACTION
    market_id, fee = factory.decodeSetFeePayload(payload)
    assert market_id == "0x" + MARKET_ID.hex()
    assert fee == NEW_FEE
