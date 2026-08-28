import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendRiskStewardActions,
    RiskStewardDashboardStub,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
ACTION = 1


def create_calldata(market_id, steward):
    payload = encode(["bytes32", "address"], [market_id, str(steward)])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def dashboard_stub(owner):
    return RiskStewardDashboardStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner, dashboard_stub):
    return LidoLendRiskStewardActions.deploy(owner, dashboard_stub, {"from": owner})


def test_create_evm_script_before_market_activation(owner, dashboard_stub, factory, stranger):
    "Must allow a preconfigured steward to be removed before the market is activated"
    dashboard_stub.setMarketSteward(UNKNOWN_MARKET_ID, stranger, True, {"from": owner})
    assert factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, stranger)) == encode_call_script(
        [
            (
                dashboard_stub.address,
                dashboard_stub.removeMarketSteward.encode_input(UNKNOWN_MARKET_ID, stranger),
            )
        ]
    )


def test_create_evm_script_not_steward(owner, dashboard_stub, factory, stranger):
    "Must revert with message 'STEWARD_NOT_FOUND' if the account is not currently a steward of the market"
    assert not dashboard_stub.isMarketSteward(MARKET_ID, stranger)

    with reverts("STEWARD_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger))


def test_create_evm_script(owner, dashboard_stub, factory, stranger):
    "Must create correct EVMScript when the account is currently a steward of the market"
    dashboard_stub.setMarketSteward(MARKET_ID, stranger, True, {"from": owner})
    assert dashboard_stub.isMarketSteward(MARKET_ID, stranger)

    calldata = create_calldata(MARKET_ID, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                dashboard_stub.address,
                dashboard_stub.removeMarketSteward.encode_input(MARKET_ID, stranger),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, stranger)
    decoded_action, payload = factory.decodeEVMScriptCallData(calldata)
    assert decoded_action == ACTION
    decoded_market_id, decoded_steward = factory.decodeRiskStewardPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_steward == stranger
