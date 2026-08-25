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
SECOND_MARKET_ID = (2).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (3).to_bytes(32, "big")
ACTION = 5


def create_payload(market_ids, account):
    return encode(["bytes32[]", "address"], [market_ids, str(account)])


def create_calldata(market_ids, account):
    payload = create_payload(market_ids, account)
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def guardian_signals_stub(owner):
    return GuardianSignalsStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, guardian_signals_stub):
    first_controller = LidoLendMarketControllerStub.deploy({"from": owner})
    first_controller.setGuardianSignals(guardian_signals_stub, {"from": owner})

    second_controller = LidoLendMarketControllerStub.deploy({"from": owner})
    second_controller.setGuardianSignals(guardian_signals_stub, {"from": owner})

    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, first_controller, {"from": owner})
    core.setMarketController(SECOND_MARKET_ID, second_controller, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendGuardianActions.deploy(owner, owner_facade, {"from": owner})


def test_create_evm_script_empty_market_ids(owner, factory, stranger):
    "Must revert with 'EMPTY_MARKETS_LIST' if no market ids were provided"
    with reverts("EMPTY_MARKETS_LIST"):
        factory.createEVMScript(owner, create_calldata([], stranger))


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for one of the market ids"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata([MARKET_ID, UNKNOWN_MARKET_ID], stranger))


def test_create_evm_script_accepts_mixed_ban_state(owner, owner_facade, guardian_signals_stub, factory, stranger):
    "Must accept a batch containing an already-unbanned market because the downstream operation is idempotent"
    guardian_signals_stub.setBanned(MARKET_ID, stranger, True, {"from": owner})
    assert guardian_signals_stub.isBanned(MARKET_ID, stranger)
    assert not guardian_signals_stub.isBanned(SECOND_MARKET_ID, stranger)

    calldata = create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger)
    assert factory.createEVMScript(owner, calldata) == encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.unbanGuardianSignals.encode_input([MARKET_ID, SECOND_MARKET_ID], stranger),
            ),
        ]
    )


def test_create_evm_script(owner, owner_facade, factory, stranger):
    "Must create a single facade call covering every market id"
    calldata = create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.unbanGuardianSignals.encode_input([MARKET_ID, SECOND_MARKET_ID], stranger),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger)
    action, payload = factory.decodeEVMScriptCallData(calldata)
    assert action == ACTION
    decoded_market_ids, decoded_account = factory.decodeUnbanAccountPayload(payload)
    assert decoded_market_ids == ["0x" + MARKET_ID.hex(), "0x" + SECOND_MARKET_ID.hex()]
    assert decoded_account == stranger
