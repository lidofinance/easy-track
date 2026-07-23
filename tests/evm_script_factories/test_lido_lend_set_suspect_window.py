import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendSetSuspectWindow,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    LidoLendOwnerStub,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
NEW_WINDOW = 7200


def create_calldata(market_id, window):
    return "0x" + encode(["bytes32", "uint256"], [market_id, window]).hex()


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
    return LidoLendSetSuspectWindow.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_WINDOW))


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


def test_create_evm_script(owner, owner_facade, guardian_signals_stub, factory):
    "Must create correct EVMScript when the new window differs from the current one (0 by default)"
    assert guardian_signals_stub.getSuspectWindow() == 0

    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, NEW_WINDOW))
    expected_evm_script = encode_call_script(
        [(owner_facade.address, owner_facade.setGuardiansSuspectWindow.encode_input(MARKET_ID, NEW_WINDOW))]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_window = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_WINDOW))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_window == NEW_WINDOW
