import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendAddGuardian,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")


def create_calldata(market_id, guardian):
    return "0x" + encode(["bytes32", "address"], [market_id, str(guardian)]).hex()


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
def factory(owner, core_stub):
    return LidoLendAddGuardian.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, stranger))


def test_create_evm_script_zero_guardian(owner, factory):
    "Must revert with message 'ZERO_GUARDIAN' if the guardian is the zero address"
    with reverts("ZERO_GUARDIAN"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS))


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, stranger))


def test_create_evm_script_already_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'GUARDIAN_ALREADY_ADDED' if the account is already a guardian"
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    assert guardian_signals_stub.isGuardian(stranger)

    with reverts("GUARDIAN_ALREADY_ADDED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger))


def test_create_evm_script(owner, guardian_signals_stub, factory, stranger):
    "Must create correct EVMScript when the account is not yet a guardian"
    assert not guardian_signals_stub.isGuardian(stranger)

    calldata = create_calldata(MARKET_ID, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                guardian_signals_stub.address,
                guardian_signals_stub.addGuardian.encode_input(stranger),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, stranger)
    decoded_market_id, decoded_guardian = factory.decodeEVMScriptCallData(calldata)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_guardian == stranger


def test_resolves_registry_per_market_id(owner, stranger):
    "The target registry is resolved from the calldata marketId — one factory serves each market's own registry, so EasyTrack's permission (bound to a resolved registry) is what scopes which market a motion can touch."
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (1).to_bytes(32, "big"), (2).to_bytes(32, "big")
    registries = {}
    for mid in (market_a, market_b):
        gs = GuardianSignalsStub.deploy({"from": owner})
        controller = LidoLendMarketControllerStub.deploy({"from": owner})
        controller.setGuardianSignals(gs, {"from": owner})
        core.setMarketController(mid, controller, {"from": owner})
        registries[mid] = gs

    factory = LidoLendAddGuardian.deploy(owner, core, {"from": owner})
    script_a = factory.createEVMScript(owner, create_calldata(market_a, stranger))
    script_b = factory.createEVMScript(owner, create_calldata(market_b, stranger))

    gs_a, gs_b = registries[market_a], registries[market_b]
    assert script_a == encode_call_script([(gs_a.address, gs_a.addGuardian.encode_input(stranger))])
    assert script_b == encode_call_script([(gs_b.address, gs_b.addGuardian.encode_input(stranger))])
    assert script_a != script_b
