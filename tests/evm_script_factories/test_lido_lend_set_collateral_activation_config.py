import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendSetCollateralActivationConfig,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    LidoLendOwnerStub,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
from utils.lido_lend import COLLATERAL_ACTIVATION_CONFIG_ABI_TYPE as CONFIG_TYPE

NEW_CONFIG = (10, 20, 30, 40, 50, 60, 30, 80, 90)
MAX_DELAY_DURATION = 7 * 24 * 60 * 60


def create_calldata(market_id, cfg):
    return "0x" + encode(["bytes32", CONFIG_TYPE], [market_id, cfg]).hex()


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
    return LidoLendSetCollateralActivationConfig.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_CONFIG))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for the market id (well-formed config)"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_CONFIG))


def test_create_evm_script_same_config(owner, controller_stub, factory):
    "Must revert with message 'SAME_CONFIG' if the new config equals the current one"
    controller_stub.setCollateralActivationConfig(NEW_CONFIG, {"from": owner})
    assert controller_stub.collateralActivationConfig() == NEW_CONFIG

    with reverts("SAME_CONFIG"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, NEW_CONFIG))


@pytest.mark.parametrize(
    "config,error",
    [
        ((0, 20, 30, 40, 50, 60, 30, 80, 90), "ZERO_MIN_ACTIVATION_DELAY"),
        ((21, 20, 30, 40, 50, 60, 30, 80, 90), "INVALID_ACTIVATION_DELAYS"),
        (
            (10, MAX_DELAY_DURATION + 1, 30, 40, 50, 60, 0, 80, 90),
            "MAX_ACTIVATION_DELAY_EXCEEDED",
        ),
        (
            (10, 20, 30, 40, MAX_DELAY_DURATION + 1, 60, 30, 80, 90),
            "MAX_ACTIVATING_LOCK_DURATION_EXCEEDED",
        ),
        ((10, 20, 30, 40, 50, 60, 20, 80, 90), "INVALID_MAX_GUARDIANS_QUORUM_DELAY"),
        # Above the cap but still above maxActivationDelay, so it clears the check before it and can only
        # be caught by the cap check itself.
        (
            (10, 20, 30, 40, 50, 60, MAX_DELAY_DURATION + 1, 80, 90),
            "MAX_GUARDIANS_QUORUM_DELAY_EXCEEDED",
        ),
        ((10, 20, 30, 40, 50, 0, 30, 80, 90), "ZERO_MIN_ACTIVATION_AMOUNT"),
        ((10, 20, 0, 40, 50, 60, 30, 80, 90), "ZERO_MAX_DELAY_INFLOW"),
        (
            (10, 20, 30, 40, 50, 60, 30, MAX_DELAY_DURATION + 1, 90),
            "MAX_DELAY_PER_STRIKE_EXCEEDED",
        ),
        (
            (10, 20, 30, 40, 50, 60, 30, 80, MAX_DELAY_DURATION + 1),
            "MAX_DELAY_PER_SUSPECT_EXCEEDED",
        ),
    ],
)
def test_create_evm_script_invalid_config(owner, factory, config, error):
    "Must reject every config that the controller would reject when the motion is enacted"
    with reverts(error):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, config))


def test_create_evm_script(owner, owner_facade, factory):
    "Must create correct EVMScript if all requirements are met"
    calldata = create_calldata(MARKET_ID, NEW_CONFIG)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                owner_facade.address,
                owner_facade.setMarketCollateralActivationConfig.encode_input(MARKET_ID, NEW_CONFIG),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_cfg = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_CONFIG))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_cfg == NEW_CONFIG
