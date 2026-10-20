import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendGuardianActions,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    LidoLendOwnerStub,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
NEW_WINDOW = 7200
MAX_SUSPECT_WINDOW = 30 * 24 * 60 * 60
ACTION = 4


def create_payload(market_id, window):
    return encode(["bytes32", "uint256"], [market_id, window])


def create_calldata(market_id, window):
    payload = create_payload(market_id, window)
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def guardian_signals_stub(owner):
    return GuardianSignalsStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, guardian_signals_stub):
    controller = LidoLendMarketControllerStub.deploy({"from": owner})
    controller.setGuardianSignals(guardian_signals_stub, {"from": owner})
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, controller, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendGuardianActions.deploy(owner, owner_facade, {"from": owner})


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_WINDOW))


def test_create_evm_script_same_suspect_window(owner, guardian_signals_stub, factory):
    "Must revert with message 'SAME_SUSPECT_WINDOW' if the new window equals the current one"
    guardian_signals_stub.setSuspectWindow(NEW_WINDOW, {"from": owner})
    assert guardian_signals_stub.getSuspectWindow() == NEW_WINDOW

    with reverts("SAME_SUSPECT_WINDOW"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, NEW_WINDOW))


def test_create_evm_script_suspect_window_too_high(owner, factory):
    "Must reject a suspect window that GuardianSignals would reject when the motion is enacted"
    with reverts("SUSPECT_WINDOW_TOO_HIGH"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, MAX_SUSPECT_WINDOW + 1))


@pytest.mark.parametrize("new_window", [NEW_WINDOW, MAX_SUSPECT_WINDOW])
def test_create_evm_script(owner, owner_facade, guardian_signals_stub, factory, new_window):
    "Must create correct EVMScript when the new window differs from the current one (0 by default)"
    assert guardian_signals_stub.getSuspectWindow() == 0

    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, new_window))
    expected_evm_script = encode_call_script(
        [(owner_facade.address, owner_facade.setGuardiansSuspectWindow.encode_input(MARKET_ID, new_window))]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    action, payload = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_WINDOW))
    assert action == ACTION
    decoded_market_id, decoded_window = factory.decodeSetSuspectWindowPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_window == NEW_WINDOW
