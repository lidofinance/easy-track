import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendSetGuardiansQuorum,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    LidoLendOwnerStub,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
NEW_QUORUM = 2


def create_calldata(market_id, quorum):
    return "0x" + encode(["bytes32", "uint256"], [market_id, quorum]).hex()


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
    return LidoLendSetGuardiansQuorum.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_QUORUM))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_QUORUM))


def test_create_evm_script_same_quorum(owner, guardian_signals_stub, factory):
    "Must revert with message 'SAME_QUORUM' if the new quorum equals the current one"
    guardian_signals_stub.setQuorum(NEW_QUORUM, {"from": owner})
    assert guardian_signals_stub.getQuorum() == NEW_QUORUM

    with reverts("SAME_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, NEW_QUORUM))


def test_create_evm_script_bad_quorum(owner, guardian_signals_stub, factory):
    "Must revert with 'INVALID_QUORUM' if the new quorum exceeds the guardian count"
    guardian_signals_stub.addGuardian(f"0x{0xa1:040x}", {"from": owner})
    with reverts("INVALID_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, NEW_QUORUM))


def test_create_evm_script_zero_quorum(owner, guardian_signals_stub, factory):
    "Must revert with 'INVALID_QUORUM' for a zero quorum (the other INVALID_QUORUM sub-branch)"
    # Current quorum must be non-zero, otherwise SAME_QUORUM would mask the zero-quorum branch.
    guardian_signals_stub.setQuorum(1, {"from": owner})
    with reverts("INVALID_QUORUM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, 0))


def test_create_evm_script(owner, owner_facade, guardian_signals_stub, factory):
    "Must create correct EVMScript when the new quorum differs and is within the guardian count"
    guardian_signals_stub.addGuardian(f"0x{0xa1:040x}", {"from": owner})
    guardian_signals_stub.addGuardian(f"0x{0xa2:040x}", {"from": owner})
    assert guardian_signals_stub.getQuorum() == 0

    calldata = create_calldata(MARKET_ID, NEW_QUORUM)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.setGuardiansQuorum.encode_input(MARKET_ID, NEW_QUORUM),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_ID, NEW_QUORUM)
    decoded_market_id, decoded_quorum = factory.decodeEVMScriptCallData(calldata)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_quorum == NEW_QUORUM
