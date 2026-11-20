import pytest
from brownie import LidoLendCircuitBreakerActions
from eth_abi import encode

ZERO_ADDRESS = "0x" + "00" * 20
EXISTING_PAUSER = "0x" + "55" * 20
REGISTER_PAUSER = 0
SET_PAUSE_DURATION = 1
SET_HEARTBEAT_INTERVAL = 2


def action_calldata(action, payload):
    return "0x" + encode(["uint8", "bytes"], [action, payload]).hex()


@pytest.mark.parametrize(
    "existing_pauser",
    [ZERO_ADDRESS, EXISTING_PAUSER],
    ids=["first-registration", "replace-existing"],
)
def test_register_pauser_scenario(
    lido_lend,
    created_market,
    easy_track,
    deployer,
    trusted_caller,
    enact_motion,
    register_factory,
    permission,
    impersonate,
    existing_pauser,
):
    "Register or replace the market's pauser on the shared CircuitBreaker."
    if not lido_lend.has("circuitBreaker"):
        if lido_lend.local:
            pytest.skip("descriptor lacks CircuitBreaker")
        raise pytest.UsageError("descriptor lacks CircuitBreaker")

    market = lido_lend.market
    if market["pauser"] == ZERO_ADDRESS:
        raise pytest.UsageError("market artifact has a zero pauser")

    core = lido_lend.contract("core")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    controller = market["controller"]
    if circuit_breaker.getPauser(controller).lower() != existing_pauser.lower():
        circuit_breaker.registerPauser(
            controller,
            existing_pauser,
            {"from": impersonate(circuit_breaker.ADMIN())},
        )
    assert circuit_breaker.getPauser(controller) == existing_pauser
    assert market["pauser"].lower() != existing_pauser.lower()

    factory = deployer.deploy(LidoLendCircuitBreakerActions, trusted_caller, core, circuit_breaker)
    register_factory(
        factory,
        permission(
            (circuit_breaker, circuit_breaker.registerPauser),
            (circuit_breaker, circuit_breaker.setPauseDuration),
            (circuit_breaker, circuit_breaker.setHeartbeatInterval),
        ),
    )

    payload = encode(["bytes32", "address"], [market["id"], market["pauser"]])
    calldata = action_calldata(REGISTER_PAUSER, payload)
    enact_motion(easy_track, factory, calldata, trusted_caller)

    assert circuit_breaker.getPauser(controller) == market["pauser"]


@pytest.mark.parametrize(
    "action,getter,min_getter,max_getter",
    [
        (SET_PAUSE_DURATION, "pauseDuration", "MIN_PAUSE_DURATION", "MAX_PAUSE_DURATION"),
        (
            SET_HEARTBEAT_INTERVAL,
            "heartbeatInterval",
            "MIN_HEARTBEAT_INTERVAL",
            "MAX_HEARTBEAT_INTERVAL",
        ),
    ],
)
def test_circuit_breaker_config_scenario(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    enact_motion,
    register_factory,
    permission,
    action,
    getter,
    min_getter,
    max_getter,
):
    circuit_breaker = lido_lend.contract("circuitBreaker")
    current = getattr(circuit_breaker, getter)()
    minimum = getattr(circuit_breaker, min_getter)()
    maximum = getattr(circuit_breaker, max_getter)()
    new_value = minimum if current != minimum else maximum

    factory = deployer.deploy(
        LidoLendCircuitBreakerActions,
        trusted_caller,
        lido_lend.contract("core"),
        circuit_breaker,
    )
    register_factory(
        factory,
        permission(
            (circuit_breaker, circuit_breaker.registerPauser),
            (circuit_breaker, circuit_breaker.setPauseDuration),
            (circuit_breaker, circuit_breaker.setHeartbeatInterval),
        ),
    )
    enact_motion(
        easy_track,
        factory,
        action_calldata(action, encode(["uint256"], [new_value])),
        trusted_caller,
    )

    assert getattr(circuit_breaker, getter)() == new_value
