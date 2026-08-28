import pytest
from eth_abi import encode
from brownie import (
    CircuitBreakerStub,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    LidoLendCircuitBreakerActions,
    ZERO_ADDRESS,
    reverts,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
REGISTER_PAUSER = 0


def create_calldata(market_id, pauser):
    payload = encode(["bytes32", "address"], [market_id, str(pauser)])
    return "0x" + encode(["uint8", "bytes"], [REGISTER_PAUSER, payload]).hex()


@pytest.fixture(scope="module")
def circuit_breaker_stub(owner):
    return CircuitBreakerStub.deploy(owner, {"from": owner})


@pytest.fixture(scope="module")
def controller(owner):
    return LidoLendMarketControllerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, controller):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, controller, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub, circuit_breaker_stub):
    return LidoLendCircuitBreakerActions.deploy(owner, core_stub, circuit_breaker_stub, {"from": owner})


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, stranger))


def test_create_evm_script_zero_pauser_unregisters(owner, circuit_breaker_stub, controller, factory):
    "Must unregister the controller's pauser when the supplied address is zero"
    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS))

    assert evm_script == encode_call_script(
        [
            (
                circuit_breaker_stub.address,
                circuit_breaker_stub.registerPauser.encode_input(controller.address, ZERO_ADDRESS),
            )
        ]
    )


def test_create_evm_script_zero_controller(owner, factory, stranger):
    "Must reject a market id that resolves to the zero controller"
    with reverts("ZERO_CONTROLLER"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, stranger))


def test_create_evm_script(owner, circuit_breaker_stub, controller, factory, stranger):
    "Must register the supplied pauser for the controller resolved from the market id"
    calldata = create_calldata(MARKET_ID, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                circuit_breaker_stub.address,
                circuit_breaker_stub.registerPauser.encode_input(controller.address, stranger),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, stranger)
    action, payload = factory.decodeEVMScriptCallData(calldata)
    assert action == REGISTER_PAUSER
    market_id, pauser = factory.decodeRegisterPauserPayload(payload)
    assert market_id == "0x" + MARKET_ID.hex()
    assert pauser == stranger


def test_rejects_unknown_action(owner, factory):
    calldata = "0x" + encode(["uint8", "bytes"], [255, b""]).hex()
    with reverts():
        factory.createEVMScript(owner, calldata)
