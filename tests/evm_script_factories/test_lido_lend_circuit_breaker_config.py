import pytest
from brownie import CircuitBreakerStub, LidoLendCircuitBreakerActions, LidoLendCoreStub, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

SET_PAUSE_DURATION = 1
SET_HEARTBEAT_INTERVAL = 2
PAUSE_DURATION = 7 * 24 * 60 * 60
HEARTBEAT_INTERVAL = 60 * 24 * 60 * 60


def calldata(action, value):
    payload = encode(["uint256"], [value])
    return "0x" + encode(["uint8", "bytes"], [action, payload]).hex()


@pytest.fixture(scope="module")
def circuit_breaker(owner):
    return CircuitBreakerStub.deploy(owner, {"from": owner})


@pytest.fixture(scope="module")
def factory(owner, circuit_breaker):
    core = LidoLendCoreStub.deploy({"from": owner})
    return LidoLendCircuitBreakerActions.deploy(owner, core, circuit_breaker, {"from": owner})


def test_create_set_pause_duration_evm_script(owner, circuit_breaker, factory):
    expected_call = circuit_breaker.setPauseDuration.encode_input(PAUSE_DURATION)

    assert factory.createEVMScript(owner, calldata(SET_PAUSE_DURATION, PAUSE_DURATION)) == encode_call_script(
        [(circuit_breaker.address, expected_call)]
    )


def test_create_set_heartbeat_interval_evm_script(owner, circuit_breaker, factory):
    expected_call = circuit_breaker.setHeartbeatInterval.encode_input(HEARTBEAT_INTERVAL)

    assert factory.createEVMScript(owner, calldata(SET_HEARTBEAT_INTERVAL, HEARTBEAT_INTERVAL)) == encode_call_script(
        [(circuit_breaker.address, expected_call)]
    )


@pytest.mark.parametrize("value", [3 * 24 * 60 * 60 - 1, 30 * 24 * 60 * 60 + 1])
def test_rejects_pause_duration_out_of_range(owner, factory, value):
    with reverts("PAUSE_DURATION_OUT_OF_RANGE"):
        factory.createEVMScript(owner, calldata(SET_PAUSE_DURATION, value))


@pytest.mark.parametrize("value", [30 * 24 * 60 * 60 - 1, 1095 * 24 * 60 * 60 + 1])
def test_rejects_heartbeat_interval_out_of_range(owner, factory, value):
    with reverts("HEARTBEAT_INTERVAL_OUT_OF_RANGE"):
        factory.createEVMScript(owner, calldata(SET_HEARTBEAT_INTERVAL, value))


def test_decode_config_value_payload(factory):
    _, payload = factory.decodeEVMScriptCallData(calldata(SET_PAUSE_DURATION, PAUSE_DURATION))
    assert factory.decodeConfigValuePayload(payload) == PAUSE_DURATION
