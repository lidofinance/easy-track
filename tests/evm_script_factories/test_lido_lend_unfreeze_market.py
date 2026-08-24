import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendMarketManagerActions,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    LidoLendOwnerStub,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
SECOND_MARKET_ID = (2).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (3).to_bytes(32, "big")
ACTION = 4


def create_calldata(market_ids):
    payload = encode(["bytes32[]"], [market_ids])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def controller_stub(owner):
    return LidoLendMarketControllerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def second_controller_stub(owner):
    return LidoLendMarketControllerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, controller_stub, second_controller_stub):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, controller_stub, {"from": owner})
    core.setMarketController(SECOND_MARKET_ID, second_controller_stub, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendMarketManagerActions.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata([MARKET_ID]))


def test_create_evm_script_empty_market_ids(owner, factory):
    "Must revert with 'EMPTY_MARKETS_LIST' if no market ids were provided"
    with reverts("EMPTY_MARKETS_LIST"):
        factory.createEVMScript(owner, create_calldata([]))


def test_create_evm_script_market_not_found(owner, controller_stub, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for one of the market ids"
    controller_stub.setFrozen(True, {"from": owner})
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata([MARKET_ID, UNKNOWN_MARKET_ID]))


def test_create_evm_script_not_frozen(owner, controller_stub, factory):
    "Must revert with message 'MARKET_IS_NOT_FROZEN' if the market is not currently frozen"
    assert not controller_stub.isFrozen()

    with reverts("MARKET_IS_NOT_FROZEN"):
        factory.createEVMScript(owner, create_calldata([MARKET_ID]))


def test_create_evm_script(owner, owner_facade, controller_stub, second_controller_stub, factory):
    "Must create one unfreeze call per frozen market"
    controller_stub.setFrozen(True, {"from": owner})
    second_controller_stub.setFrozen(True, {"from": owner})
    assert controller_stub.isFrozen()
    assert second_controller_stub.isFrozen()

    evm_script = factory.createEVMScript(owner, create_calldata([MARKET_ID, SECOND_MARKET_ID]))

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.unfreezeMarket.encode_input(MARKET_ID),
            ),
            (
                owner_facade.address,
                owner_facade.unfreezeMarket.encode_input(SECOND_MARKET_ID),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_action, payload = factory.decodeEVMScriptCallData(create_calldata([MARKET_ID, SECOND_MARKET_ID]))
    assert decoded_action == ACTION
    assert factory.decodeUnfreezeMarketPayload(payload) == [
        "0x" + MARKET_ID.hex(),
        "0x" + SECOND_MARKET_ID.hex(),
    ]
