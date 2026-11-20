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
from utils.lido_lend import SETTLEMENT_CONFIG_ABI_TYPE as CONFIG_TYPE

NEW_CONFIG = (100, 200, 300, 400)
ACTION = 2


def create_calldata(market_id, cfg):
    payload = encode(["bytes32", CONFIG_TYPE], [market_id, cfg])
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
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id (well-formed config)"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_CONFIG))


def test_create_evm_script_same_config(owner, controller_stub, factory):
    "Must revert with message 'SAME_CONFIG' if the new config equals the current one"
    controller_stub.setSettlementConfig(NEW_CONFIG, {"from": owner})
    assert controller_stub.settlementConfig() == NEW_CONFIG

    with reverts("SAME_CONFIG"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, NEW_CONFIG))


@pytest.mark.parametrize(
    "config",
    [
        (10_001, 200, 300, 400),
        (100, 200, 300, 10_001),
    ],
)
def test_create_evm_script_config_out_of_range(owner, factory, config):
    "Must reject BPS values that the controller would reject when the motion is enacted"
    with reverts("SETTLEMENT_CONFIG_OUT_OF_RANGE"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, config))


@pytest.mark.parametrize("config", [NEW_CONFIG, (10_000, 200, 300, 10_000)])
def test_create_evm_script(owner, owner_facade, factory, config):
    "Must create correct EVMScript if all requirements are met"
    calldata = create_calldata(MARKET_ID, config)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.setMarketSettlementConfig.encode_input(MARKET_ID, config),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_action, payload = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_CONFIG))
    assert decoded_action == ACTION
    decoded_market_id, decoded_cfg = factory.decodeSetSettlementConfigPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_cfg == NEW_CONFIG
