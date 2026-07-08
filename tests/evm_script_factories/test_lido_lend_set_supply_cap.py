import pytest
from eth_abi import encode
from brownie import reverts, LidoLendSetSupplyCap, LidoLendCoreStub, LidoLendMarketControllerStub

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
def factory(owner, core_stub):
    return LidoLendSetSupplyCap.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_CAP))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_CAP))


def test_create_evm_script_zero_cap(owner, controller_stub, factory):
    "Must revert with message 'CAP_NOT_HIGHER' if the new cap is zero (0 means uncapped)"
    assert controller_stub.supplyCap() == 0
    with reverts("CAP_NOT_HIGHER"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, 0))


def test_create_evm_script_cap_not_higher(owner, controller_stub, factory):
    "Must revert with message 'CAP_NOT_HIGHER' if the new cap equals or is below the current one"
    controller_stub.setSupplyCap(500, {"from": owner})
    assert controller_stub.supplyCap() == 500

    with reverts("CAP_NOT_HIGHER"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, 500))

    with reverts("CAP_NOT_HIGHER"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, 400))


def test_create_evm_script_accepts_cap_above_current(owner, controller_stub, factory):
    "Must accept a new cap exactly one above the current one"
    controller_stub.setSupplyCap(500, {"from": owner})

    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, 501))
    expected_evm_script = encode_call_script(
        [
            (
                controller_stub.address,
                controller_stub.setSupplyCap.encode_input(501),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_create_evm_script(owner, controller_stub, factory):
    "Must create correct EVMScript when the new cap is higher than the current one (0 by default)"
    assert controller_stub.supplyCap() == 0

    calldata = create_calldata(MARKET_ID, NEW_CAP)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                controller_stub.address,
                controller_stub.setSupplyCap.encode_input(NEW_CAP),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_cap = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_CAP))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_cap == NEW_CAP


def test_resolves_controller_per_market_id(owner):
    "The target controller is resolved from the calldata marketId — one factory serves each market's controller."
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (1).to_bytes(32, "big"), (2).to_bytes(32, "big")
    ctrl_a = LidoLendMarketControllerStub.deploy({"from": owner})
    ctrl_b = LidoLendMarketControllerStub.deploy({"from": owner})
    core.setMarketController(market_a, ctrl_a, {"from": owner})
    core.setMarketController(market_b, ctrl_b, {"from": owner})

    factory = LidoLendSetSupplyCap.deploy(owner, core, {"from": owner})
    script_a = factory.createEVMScript(owner, create_calldata(market_a, NEW_CAP))
    script_b = factory.createEVMScript(owner, create_calldata(market_b, NEW_CAP))

    assert script_a == encode_call_script([(ctrl_a.address, ctrl_a.setSupplyCap.encode_input(NEW_CAP))])
    assert script_b == encode_call_script([(ctrl_b.address, ctrl_b.setSupplyCap.encode_input(NEW_CAP))])
    assert script_a != script_b
