import pytest
from brownie import reverts

from utils.evm_script import encode_call_script, encode_calldata


INITIAL_DEPOSITS_RESERVE_TARGET = 1500 * 10**18
MAX_DEPOSITS_RESERVE_TARGET = 3000 * 10**18


def create_calldata(deposits_reserve_target):
    return encode_calldata(["uint256"], [deposits_reserve_target])


@pytest.fixture(scope="module")
def lido_stub(owner, LidoStub):
    return owner.deploy(LidoStub, INITIAL_DEPOSITS_RESERVE_TARGET)


@pytest.fixture(scope="module")
def set_deposits_reserve_target_factory(owner, lido_stub, SetDepositsReserveTarget):
    return owner.deploy(
        SetDepositsReserveTarget,
        owner,
        MAX_DEPOSITS_RESERVE_TARGET,
        lido_stub,
    )


def test_deploy(owner, lido_stub, set_deposits_reserve_target_factory):
    assert set_deposits_reserve_target_factory.trustedCaller() == owner
    assert set_deposits_reserve_target_factory.MAX_DEPOSITS_RESERVE_TARGET() == MAX_DEPOSITS_RESERVE_TARGET
    assert set_deposits_reserve_target_factory.lido() == lido_stub


def test_create_evm_script(owner, lido_stub, set_deposits_reserve_target_factory):
    new_deposits_reserve_target = 2000 * 10**18
    calldata = create_calldata(new_deposits_reserve_target)

    evm_script = set_deposits_reserve_target_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                lido_stub.address,
                lido_stub.setDepositsReserveTarget.encode_input(new_deposits_reserve_target),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_accepts_max_deposits_reserve_target(owner, set_deposits_reserve_target_factory):
    calldata = create_calldata(MAX_DEPOSITS_RESERVE_TARGET)

    set_deposits_reserve_target_factory.createEVMScript(owner, calldata)


def test_accepts_zero_deposits_reserve_target(owner, set_deposits_reserve_target_factory):
    calldata = create_calldata(0)

    set_deposits_reserve_target_factory.createEVMScript(owner, calldata)


def test_reverts_if_deposits_reserve_target_is_too_high(owner, set_deposits_reserve_target_factory):
    calldata = create_calldata(MAX_DEPOSITS_RESERVE_TARGET + 1)

    with reverts("DEPOSITS_RESERVE_TARGET_TOO_HIGH"):
        set_deposits_reserve_target_factory.createEVMScript(owner, calldata)


def test_reverts_if_deposits_reserve_target_is_unchanged(owner, set_deposits_reserve_target_factory):
    calldata = create_calldata(INITIAL_DEPOSITS_RESERVE_TARGET)

    with reverts("SAME_DEPOSITS_RESERVE_TARGET"):
        set_deposits_reserve_target_factory.createEVMScript(owner, calldata)


def test_reverts_if_creator_is_not_trusted(stranger, set_deposits_reserve_target_factory):
    calldata = create_calldata(2000 * 10**18)

    with reverts("CALLER_IS_FORBIDDEN"):
        set_deposits_reserve_target_factory.createEVMScript(stranger, calldata)


def test_reverts_if_calldata_is_malformed(owner, set_deposits_reserve_target_factory):
    with reverts():
        set_deposits_reserve_target_factory.createEVMScript(owner, "0x00")


def test_decode_evm_script_call_data(set_deposits_reserve_target_factory):
    deposits_reserve_target = 2000 * 10**18
    calldata = create_calldata(deposits_reserve_target)

    decoded_deposits_reserve_target = set_deposits_reserve_target_factory.decodeEVMScriptCallData(calldata)

    assert decoded_deposits_reserve_target == deposits_reserve_target
