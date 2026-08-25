import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendMarketManagerActions,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    LidoLendOwnerStub,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
CALLER = "0x" + "a1" * 20
ACTION = 0


def create_calldata(market_id, caller, enabled):
    payload = encode(["bytes32", "address", "bool"], [market_id, str(caller), enabled])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def controller_stub(owner):
    return LidoLendMarketControllerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, controller_stub):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, controller_stub, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendMarketManagerActions.deploy(owner, owner_facade, {"from": owner})


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, CALLER, True))


def test_create_evm_script_zero_caller(owner, factory):
    "Must revert with message 'ZERO_CALLER' if the caller is the zero address"
    with reverts("ZERO_CALLER"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS, True))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, CALLER, True))


@pytest.mark.parametrize("enabled", [True, False])
def test_create_evm_script_same_status(owner, controller_stub, factory, enabled):
    "Must revert if the caller already has the requested instant activation status"
    controller_stub.setInstantActivation(CALLER, enabled, {"from": owner})

    with reverts("SAME_INSTANT_ACTIVATION_STATUS"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, CALLER, enabled))


@pytest.mark.parametrize("enabled", [True, False])
def test_create_evm_script(owner, owner_facade, controller_stub, factory, enabled):
    "Must create correct EVMScript when changing the caller's instant activation status"
    controller_stub.setInstantActivation(CALLER, not enabled, {"from": owner})

    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, CALLER, enabled))
    expected_evm_script = encode_call_script(
        [(owner_facade.address, owner_facade.setInstantActivation.encode_input(MARKET_ID, CALLER, enabled))]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_action, payload = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, CALLER, True))
    assert decoded_action == ACTION
    decoded_market_id, decoded_caller, decoded_enabled = factory.decodeSetInstantActivationPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_caller == CALLER
    assert decoded_enabled is True


def test_rejects_unknown_action(owner, factory):
    calldata = "0x" + encode(["uint8", "bytes"], [255, b""]).hex()
    with reverts():
        factory.createEVMScript(owner, calldata)
