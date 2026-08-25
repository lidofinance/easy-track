import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendGuardianActions,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    LidoLendOwnerStub,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
ACTION = 0


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


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, stranger, 1))


def test_create_evm_script_zero_guardian(owner, factory):
    "Must revert with message 'ZERO_GUARDIAN' if the guardian is the zero address"
    with reverts("ZERO_GUARDIAN"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS, 1))


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, stranger, 1))


def test_create_evm_script_already_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'GUARDIAN_ALREADY_ADDED' if the account is already a guardian"
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})
    assert guardian_signals_stub.isGuardian(stranger)

    with reverts("GUARDIAN_ALREADY_ADDED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger, 1))


def test_create_evm_script_max_guardians_reached(owner, guardian_signals_stub, factory):
    "Must reject the 33rd guardian before creating a motion that would fail when enacted"
    for guardian_number in range(1, 33):
        guardian_signals_stub.setGuardian(f"0x{guardian_number:040x}", True, {"from": owner})
    assert guardian_signals_stub.getGuardianCount() == guardian_signals_stub.MAX_GUARDIANS_COUNT() == 32

    with reverts("MAX_GUARDIANS_REACHED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, f"0x{33:040x}", 1))


@pytest.mark.parametrize("new_quorum", [0, 2])
def test_create_evm_script_invalid_quorum(owner, factory, stranger, new_quorum):
    "Must reject a quorum that is invalid after adding the first guardian"
    with reverts("INVALID_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger, new_quorum))


def test_create_evm_script(owner, owner_facade, guardian_signals_stub, factory, stranger):
    "Must add the guardian and set the requested quorum"
    assert not guardian_signals_stub.isGuardian(stranger)
    guardian_signals_stub.setGuardian("0x" + "44" * 20, True, {"from": owner})
    guardian_signals_stub.setGuardian("0x" + "55" * 20, True, {"from": owner})
    guardian_signals_stub.setGuardian("0x" + "66" * 20, True, {"from": owner})
    guardian_signals_stub.setQuorum(3, {"from": owner})

    calldata = create_calldata(MARKET_ID, stranger, 4)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.addGuardian.encode_input(MARKET_ID, stranger),
            ),
            (
                owner_facade.address,
                owner_facade.setGuardiansQuorum.encode_input(MARKET_ID, 4),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, stranger, 4)
    action, payload = factory.decodeEVMScriptCallData(calldata)
    assert action == ACTION
    decoded_market_id, decoded_guardian, decoded_new_quorum = factory.decodeAddGuardianPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_guardian == stranger
    assert decoded_new_quorum == 4


def test_rejects_unknown_action(owner, factory):
    calldata = "0x" + encode(["uint8", "bytes"], [255, b""]).hex()
    with reverts():
        factory.createEVMScript(owner, calldata)
