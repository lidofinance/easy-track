import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendRiskStewardActions,
    RiskStewardDashboardStub,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
ACTION = 0


def create_calldata(market_id, steward):
    payload = encode(["bytes32", "address"], [market_id, str(steward)])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def dashboard_stub(owner, core_stub):
    dashboard = RiskStewardDashboardStub.deploy({"from": owner})
    dashboard.setLidoLend(core_stub, {"from": owner})
    return dashboard


@pytest.fixture(scope="module")
def core_stub(owner):
    "A core with a controller registered for MARKET_ID, so the market-existence check resolves."
    controller = LidoLendMarketControllerStub.deploy({"from": owner})
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, controller, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, dashboard_stub):
    return LidoLendRiskStewardActions.deploy(owner, dashboard_stub, {"from": owner})


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, stranger))


def test_create_evm_script_zero_steward(owner, factory):
    "Must revert with message 'ZERO_STEWARD' if the steward is the zero address"
    with reverts("ZERO_STEWARD"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS))


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, stranger))


def test_create_evm_script_already_steward(owner, dashboard_stub, factory, stranger):
    "Must revert with message 'STEWARD_ALREADY_ADDED' if the account is already a steward of the market"
    dashboard_stub.setMarketSteward(MARKET_ID, stranger, True, {"from": owner})
    assert dashboard_stub.isMarketSteward(MARKET_ID, stranger)

    with reverts("STEWARD_ALREADY_ADDED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger))


def test_create_evm_script(owner, dashboard_stub, factory, stranger):
    "Must create correct EVMScript when the account is not yet a steward of the market"
    assert not dashboard_stub.isMarketSteward(MARKET_ID, stranger)

    calldata = create_calldata(MARKET_ID, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                dashboard_stub.address,
                dashboard_stub.addMarketSteward.encode_input(MARKET_ID, stranger),
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


def test_rejects_unknown_action(owner, factory):
    calldata = "0x" + encode(["uint8", "bytes"], [255, b""]).hex()
    with reverts():
        factory.createEVMScript(owner, calldata)
