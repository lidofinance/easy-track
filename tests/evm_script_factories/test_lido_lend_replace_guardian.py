import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendReplaceGuardian,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    LidoLendOwnerStub,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
OLD_GUARDIAN = f"0x{5:040x}"


def create_calldata(market_id, old_guardian, new_guardian):
    return (
        "0x"
        + encode(
            ["bytes32", "address", "address"],
            [market_id, str(old_guardian), str(new_guardian)],
        ).hex()
    )


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
    return LidoLendReplaceGuardian.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must reject a creator other than the trusted caller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(
            stranger,
            create_calldata(MARKET_ID, OLD_GUARDIAN, stranger),
        )


def test_create_evm_script_zero_new_guardian(owner, factory):
    "Must reject the zero address as the replacement guardian"
    with reverts("ZERO_GUARDIAN"):
        factory.createEVMScript(
            owner,
            create_calldata(MARKET_ID, OLD_GUARDIAN, ZERO_ADDRESS),
        )


def test_create_evm_script_market_not_found(owner, factory, stranger):
    "Must reject an unknown market"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(
            owner,
            create_calldata(UNKNOWN_MARKET_ID, OLD_GUARDIAN, stranger),
        )


def test_create_evm_script_old_not_guardian(owner, guardian_signals_stub, factory, stranger):
    "Must reject an account that is not currently a guardian"
    assert not guardian_signals_stub.isGuardian(OLD_GUARDIAN)
    with reverts("GUARDIAN_NOT_FOUND"):
        factory.createEVMScript(
            owner,
            create_calldata(MARKET_ID, OLD_GUARDIAN, stranger),
        )


def test_create_evm_script_new_already_guardian(
    owner,
    guardian_signals_stub,
    factory,
    stranger,
):
    "Must reject a replacement that is already a guardian"
    guardian_signals_stub.setGuardian(OLD_GUARDIAN, True, {"from": owner})
    guardian_signals_stub.setGuardian(stranger, True, {"from": owner})

    with reverts("GUARDIAN_ALREADY_ADDED"):
        factory.createEVMScript(
            owner,
            create_calldata(MARKET_ID, OLD_GUARDIAN, stranger),
        )


def test_create_evm_script_at_full_quorum(owner, guardian_signals_stub, factory, stranger):
    "Full quorum is valid because LidoLendOwner performs the temporary quorum adjustment atomically"
    guardian_signals_stub.setGuardian(OLD_GUARDIAN, True, {"from": owner})
    guardian_signals_stub.setQuorum(1, {"from": owner})

    factory.createEVMScript(
        owner,
        create_calldata(MARKET_ID, OLD_GUARDIAN, stranger),
    )


def test_create_evm_script(owner, owner_facade, guardian_signals_stub, factory, stranger):
    "Must create one facade call instead of separate remove/add calls"
    guardian_signals_stub.setGuardian(OLD_GUARDIAN, True, {"from": owner})

    calldata = create_calldata(MARKET_ID, OLD_GUARDIAN, stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.replaceGuardian.encode_input(
                    MARKET_ID,
                    OLD_GUARDIAN,
                    stranger,
                ),
            )
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
