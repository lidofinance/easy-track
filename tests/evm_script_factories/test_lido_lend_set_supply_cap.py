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
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
NEW_CAP = 1_000_000 * 10**18
ACTION = 3


def create_calldata(market_id, cap):
    payload = encode(["bytes32", "uint256"], [market_id, cap])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


@pytest.fixture(scope="module")
def controller_stub(owner):
    return LidoLendMarketControllerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, controller_stub):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, controller_stub, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendMarketManagerActions.deploy(owner, owner_facade, {"from": owner})


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_CAP))


@pytest.mark.parametrize("new_cap", [0, 400, 500, 501])
def test_create_evm_script_accepts_any_cap(owner, owner_facade, controller_stub, factory, new_cap):
    "Must accept zero, lower, equal, and higher supply caps"
    controller_stub.setSupplyCap(500, {"from": owner})

    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, new_cap))
    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.setMarketSupplyCap.encode_input(MARKET_ID, new_cap),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_action, payload = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_CAP))
    assert decoded_action == ACTION
    decoded_market_id, decoded_cap = factory.decodeSetSupplyCapPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_cap == NEW_CAP
