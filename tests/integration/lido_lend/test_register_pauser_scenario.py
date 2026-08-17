import pytest
from brownie import LidoLendRegisterPauser
from eth_abi import encode

ZERO_ADDRESS = "0x" + "00" * 20
EXISTING_PAUSER = "0x" + "55" * 20


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

    factory = deployer.deploy(LidoLendRegisterPauser, trusted_caller, core, circuit_breaker)
    register_factory(factory, permission((circuit_breaker, circuit_breaker.registerPauser)))

    calldata = "0x" + encode(["bytes32", "address"], [market["id"], market["pauser"]]).hex()
    enact_motion(easy_track, factory, calldata, trusted_caller)

    assert circuit_breaker.getPauser(controller) == market["pauser"]
