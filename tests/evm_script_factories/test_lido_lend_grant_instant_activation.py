import pytest
from eth_abi import encode
from brownie import reverts, LidoLendGrantInstantActivation, LidoLendCoreStub, LidoLendMarketControllerStub, ZERO_ADDRESS

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
CALLER = "0x" + "a1" * 20


def create_calldata(market_id, caller):
    return "0x" + encode(["bytes32", "address"], [market_id, str(caller)]).hex()


@pytest.fixture(scope="module")
def controller_stub(owner):
    return LidoLendMarketControllerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, controller_stub):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, controller_stub, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub):
    return LidoLendGrantInstantActivation.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, CALLER))


def test_create_evm_script_zero_caller(owner, factory):
    "Must revert with message 'ZERO_CALLER' if the caller is the zero address"
    with reverts("ZERO_CALLER"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, CALLER))


def test_create_evm_script_already_granted(owner, controller_stub, factory):
    "Must revert with message 'INSTANT_ACTIVATION_ALREADY_GRANTED' if the caller already has it"
    controller_stub.grantInstantActivation(CALLER, {"from": owner})
    assert controller_stub.hasInstantActivation(CALLER)

    with reverts("INSTANT_ACTIVATION_ALREADY_GRANTED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, CALLER))


def test_create_evm_script(owner, controller_stub, factory):
    "Must create correct EVMScript when the caller does not yet have instant activation"
    assert not controller_stub.hasInstantActivation(CALLER)

    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, CALLER))
    expected_evm_script = encode_call_script(
        [(controller_stub.address, controller_stub.grantInstantActivation.encode_input(CALLER))]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_caller = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, CALLER))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_caller == CALLER
