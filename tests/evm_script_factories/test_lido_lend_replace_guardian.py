import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendReplaceGuardian,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
OLD_GUARDIAN = f"0x{5:040x}"


def create_calldata(market_id, old_guardian, new_guardian):
    return "0x" + encode(["bytes32", "address", "address"], [market_id, str(old_guardian), str(new_guardian)]).hex()


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
    return LidoLendReplaceGuardian.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, OLD_GUARDIAN, stranger))


def test_create_evm_script_zero_new_guardian(owner, factory):
    "Must revert with message 'ZERO_GUARDIAN' if the new guardian is the zero address"
    with reverts("ZERO_GUARDIAN"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, OLD_GUARDIAN, ZERO_ADDRESS))


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, OLD_GUARDIAN, stranger))


def test_create_evm_script_old_not_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'GUARDIAN_NOT_FOUND' if the old guardian is not currently a guardian"
    assert not guardian_signals_stub.isGuardian(OLD_GUARDIAN)

    with reverts("GUARDIAN_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, OLD_GUARDIAN, stranger))


def test_create_evm_script_new_already_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'GUARDIAN_ALREADY_ADDED' if the new guardian is already a guardian"
    guardian_signals_stub.setGuardian(OLD_GUARDIAN, True, {"from": owner})
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})

    with reverts("GUARDIAN_ALREADY_ADDED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, OLD_GUARDIAN, stranger))


def test_create_evm_script_would_break_quorum(owner, guardian_signals_stub, factory, stranger):
    "Must revert at creation if removing the old guardian first would drop the set below quorum"
    guardian_signals_stub.setGuardian(OLD_GUARDIAN, True, {"from": owner})
    guardian_signals_stub.setQuorum(1, {"from": owner})
    with reverts("WOULD_BREAK_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, OLD_GUARDIAN, stranger))


def test_create_evm_script_old_equals_new(owner, guardian_signals_stub, factory):
    "Must revert with 'GUARDIAN_ALREADY_ADDED' if old == new (the new guardian is, by definition, already a guardian)"
    guardian_signals_stub.setGuardian(OLD_GUARDIAN, True, {"from": owner})
    with reverts("GUARDIAN_ALREADY_ADDED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, OLD_GUARDIAN, OLD_GUARDIAN))


def test_create_evm_script(owner, guardian_signals_stub, factory, stranger):
    "Must create correct EVMScript (remove old + add new) when old is a guardian and new is not"
    guardian_signals_stub.setGuardian(OLD_GUARDIAN, True, {"from": owner})
    assert guardian_signals_stub.isGuardian(OLD_GUARDIAN)
    assert not guardian_signals_stub.isGuardian(stranger)

    calldata = create_calldata(MARKET_ID, OLD_GUARDIAN, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                guardian_signals_stub.address,
                guardian_signals_stub.removeGuardian.encode_input(OLD_GUARDIAN),
            ),
            (
                guardian_signals_stub.address,
                guardian_signals_stub.addGuardian.encode_input(stranger),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, OLD_GUARDIAN, stranger)
    decoded_market_id, decoded_old, decoded_new = factory.decodeEVMScriptCallData(calldata)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_old == OLD_GUARDIAN
    assert decoded_new == stranger
