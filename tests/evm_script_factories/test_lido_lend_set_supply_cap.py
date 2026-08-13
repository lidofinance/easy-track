import pytest
from eth_abi import encode
from brownie import reverts, LidoLendSetSupplyCap, LidoLendCoreStub, LidoLendMarketControllerStub, LidoLendOwnerStub

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
NEW_CAP = 1_000_000 * 10**18


def create_calldata(market_id, cap):
    return "0x" + encode(["bytes32", "uint256"], [market_id, cap]).hex()


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
    return LidoLendSetSupplyCap.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_CAP))


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


def test_create_evm_script(owner, owner_facade, controller_stub, factory):
    "Must create correct EVMScript for the requested cap"
    assert controller_stub.supplyCap() == 0

    calldata = create_calldata(MARKET_ID, NEW_CAP)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.setMarketSupplyCap.encode_input(MARKET_ID, NEW_CAP),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_cap = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_CAP))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_cap == NEW_CAP


def test_targets_facade_for_every_market(owner):
    "The controller is resolved from the calldata marketId inside the facade, so the factory always targets the one fixed facade — one registration serves every market. Two markets yield scripts that differ only by the embedded marketId, never the target."
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (1).to_bytes(32, "big"), (2).to_bytes(32, "big")
    ctrl_a = LidoLendMarketControllerStub.deploy({"from": owner})
    ctrl_b = LidoLendMarketControllerStub.deploy({"from": owner})
    core.setMarketController(market_a, ctrl_a, {"from": owner})
    core.setMarketController(market_b, ctrl_b, {"from": owner})
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core, {"from": owner})

    factory = LidoLendSetSupplyCap.deploy(owner, facade, {"from": owner})
    script_a = factory.createEVMScript(owner, create_calldata(market_a, NEW_CAP))
    script_b = factory.createEVMScript(owner, create_calldata(market_b, NEW_CAP))

    assert script_a == encode_call_script([(facade.address, facade.setMarketSupplyCap.encode_input(market_a, NEW_CAP))])
    assert script_b == encode_call_script([(facade.address, facade.setMarketSupplyCap.encode_input(market_b, NEW_CAP))])
    assert script_a != script_b
