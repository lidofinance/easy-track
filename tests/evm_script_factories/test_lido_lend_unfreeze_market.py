import pytest
from eth_abi import encode
from brownie import reverts, LidoLendUnfreezeMarket, LidoLendCoreStub, LidoLendMarketControllerStub

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")


def create_calldata(market_id):
    return "0x" + encode(["bytes32"], [market_id]).hex()


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
    return LidoLendUnfreezeMarket.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID))


def test_create_evm_script_not_frozen(owner, controller_stub, factory):
    "Must revert with message 'MARKET_IS_NOT_FROZEN' if the market is not currently frozen"
    assert not controller_stub.isFrozen()

    with reverts("MARKET_IS_NOT_FROZEN"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID))


def test_create_evm_script(owner, controller_stub, factory):
    "Must create correct EVMScript when the market is currently frozen"
    controller_stub.setFrozen(True, {"from": owner})
    assert controller_stub.isFrozen()

    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID))

    expected_evm_script = encode_call_script(
        [
            (
                controller_stub.address,
                controller_stub.unfreeze.encode_input(),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    assert factory.decodeEVMScriptCallData(create_calldata(MARKET_ID)) == "0x" + MARKET_ID.hex()
