import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendRemoveGuardian,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
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
    return LidoLendRemoveGuardian.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, stranger))


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, stranger))


def test_create_evm_script_not_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'GUARDIAN_NOT_FOUND' if the account is not currently a guardian"
    assert not guardian_signals_stub.isGuardian(stranger)

    with reverts("GUARDIAN_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger))


def test_create_evm_script_would_break_quorum(owner, guardian_signals_stub, factory, stranger):
    "Must revert with 'WOULD_BREAK_QUORUM' if removing the guardian would drop the set below quorum"
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    guardian_signals_stub.setQuorum(1, {"from": owner})
    with reverts("WOULD_BREAK_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger))


def test_create_evm_script(owner, guardian_signals_stub, factory, stranger):
    "Must create correct EVMScript when the account is currently a guardian"
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    assert guardian_signals_stub.isGuardian(stranger)

    calldata = create_calldata(MARKET_ID, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                guardian_signals_stub.address,
                guardian_signals_stub.removeGuardian.encode_input(stranger),
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
