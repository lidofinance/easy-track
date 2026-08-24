import pytest
from brownie import LidoLendCoreStub, LidoLendOwnerStub, LidoLendSetFee, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
NEW_FEE = 10**17


def create_calldata(market_id, new_fee):
    return "0x" + encode(["bytes32", "uint256"], [market_id, new_fee]).hex()


@pytest.fixture(scope="module")
def market_params(owner, stranger):
    return (owner.address, stranger.address, owner.address, stranger.address, 8 * 10**17)


@pytest.fixture(scope="module")
def core_stub(owner, market_params):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.activateMarket(MARKET_ID, market_params, False, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    core_stub.setOwner(facade, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendSetFee.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, factory):
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade


def test_create_evm_script_called_by_stranger(stranger, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_FEE))


def test_create_evm_script_market_not_found(owner, factory):
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_FEE))


def test_create_evm_script_fee_already_set(owner, factory):
    with reverts("FEE_ALREADY_SET"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, 0))


def test_create_evm_script_uses_target_internal_accrual(owner, owner_facade, market_params, factory):
    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, NEW_FEE))

    assert evm_script == encode_call_script(
        [(owner_facade.address, owner_facade.setFee.encode_input(market_params, NEW_FEE))]
    )


def test_decode_evm_script_call_data(factory):
    decoded_market_id, decoded_fee = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_FEE))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_fee == NEW_FEE
