import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendUnbanGuardianSignals,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")


def create_calldata(market_id, account):
    return "0x" + encode(["bytes32", "address"], [market_id, str(account)]).hex()


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
    return LidoLendUnbanGuardianSignals.deploy(owner, core_stub, {"from": owner})


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


def test_create_evm_script_not_banned(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'ACCOUNT_IS_NOT_BANNED' if the account is not currently banned on the market"
    assert not guardian_signals_stub.isBanned(MARKET_ID, stranger)

    with reverts("ACCOUNT_IS_NOT_BANNED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, stranger))


def test_create_evm_script(owner, guardian_signals_stub, factory, stranger):
    "Must create correct EVMScript when the account is currently banned on the market"
    guardian_signals_stub.setBanned(MARKET_ID, stranger, True, {"from": owner})
    assert guardian_signals_stub.isBanned(MARKET_ID, stranger)

    calldata = create_calldata(MARKET_ID, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                guardian_signals_stub.address,
                guardian_signals_stub.unban.encode_input(MARKET_ID, stranger),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, stranger)
    decoded_market_id, decoded_account = factory.decodeEVMScriptCallData(calldata)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_account == stranger
