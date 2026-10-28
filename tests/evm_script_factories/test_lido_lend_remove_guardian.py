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
ACTION = 1


def create_payload(market_id, guardian, new_quorum):
    return encode(
        ["bytes32", "address", "uint256"],
        [market_id, str(guardian), new_quorum],
    )


def create_calldata(market_id, guardian, new_quorum):
    payload = create_payload(market_id, guardian, new_quorum)
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


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, stranger, 1))


def test_create_evm_script_not_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'GUARDIAN_NOT_FOUND' if the account is not currently a guardian"
    assert not guardian_signals_stub.isGuardian(stranger)

    with reverts("GUARDIAN_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger, 1))


def test_create_evm_script_last_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must not remove the last guardian"
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    guardian_signals_stub.setQuorum(1, {"from": owner})
    with reverts("INVALID_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger, 1))


def test_create_evm_script_zero_quorum(owner, guardian_signals_stub, factory, stranger):
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    guardian_signals_stub.setGuardian("0x" + "44" * 20, True, {"from": owner})
    with reverts("INVALID_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger, 0))


def test_create_evm_script_quorum_exceeds_remaining_guardians(owner, guardian_signals_stub, factory, stranger):
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    guardian_signals_stub.setGuardian("0x" + "44" * 20, True, {"from": owner})
    guardian_signals_stub.setGuardian("0x" + "55" * 20, True, {"from": owner})
    guardian_signals_stub.setQuorum(3, {"from": owner})
    with reverts("INVALID_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger, 3))


@pytest.mark.parametrize("current_quorum,new_quorum", [(2, 1), (1, 1), (1, 2)])
def test_create_evm_script(
    owner,
    owner_facade,
    guardian_signals_stub,
    factory,
    stranger,
    current_quorum,
    new_quorum,
):
    "Must set the requested quorum before removing the guardian"
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    guardian_signals_stub.setGuardian("0x" + "44" * 20, True, {"from": owner})
    guardian_signals_stub.setGuardian("0x" + "55" * 20, True, {"from": owner})
    guardian_signals_stub.setQuorum(current_quorum, {"from": owner})
    assert guardian_signals_stub.isGuardian(stranger)

    calldata = create_calldata(MARKET_ID, stranger, new_quorum)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.setGuardiansQuorum.encode_input(MARKET_ID, new_quorum),
            ),
            (
                owner_facade.address,
                owner_facade.removeGuardian.encode_input(MARKET_ID, stranger),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, stranger, 1)
    action, payload = factory.decodeEVMScriptCallData(calldata)
    assert action == ACTION
    decoded_market_id, decoded_guardian, decoded_new_quorum = factory.decodeRemoveGuardianPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_guardian == stranger
    assert decoded_new_quorum == 1
