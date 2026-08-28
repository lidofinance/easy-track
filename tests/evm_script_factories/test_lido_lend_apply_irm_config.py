from brownie import (
    LidoLendApplyIrmConfig,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    IrmRouterStub,
    AdaptiveCurveIrmStub,
    ZERO_ADDRESS,
    reverts,
)
from eth_abi import encode
import pytest

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")

LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
IRM_CONFIG = f"0x{4:040x}"
LLTV = 800000000000000000


def create_calldata(market_id, irm_config=IRM_CONFIG):
    return "0x" + encode(["bytes32", "address"], [market_id, irm_config]).hex()


@pytest.fixture(scope="module")
def router_stub(owner):
    return IrmRouterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def adaptive_curve_irm_stub(owner):
    return AdaptiveCurveIrmStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def market_params(router_stub):
    return (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router_stub.address, LLTV)


@pytest.fixture(scope="module")
def controller_stub(owner):
    return LidoLendMarketControllerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, market_params, controller_stub):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketParams(MARKET_ID, market_params, {"from": owner})
    core.setMarketController(MARKET_ID, controller_stub, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub, router_stub, adaptive_curve_irm_stub):
    return LidoLendApplyIrmConfig.deploy(
        owner,
        core_stub,
        router_stub,
        adaptive_curve_irm_stub,
        {"from": owner},
    )


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID))


def test_create_evm_script_zero_irm_config(owner, factory):
    with reverts("ZERO_IRM_CONFIG"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the market was never created on the core (no params.irm)"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID))


def test_create_evm_script_irm_not_router(owner, core_stub, factory):
    "Must reject a market whose id commits to an IRM other than the configured domain router"
    foreign_router = IrmRouterStub.deploy({"from": owner})
    foreign_market_id = (3).to_bytes(32, "big")
    foreign_params = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, foreign_router.address, LLTV)
    core_stub.setMarketParams(foreign_market_id, foreign_params, {"from": owner})

    with reverts("IRM_NOT_ROUTER"):
        factory.createEVMScript(owner, create_calldata(foreign_market_id))


def test_create_evm_script_market_paused(owner, controller_stub, factory):
    controller_stub.setPaused(True, {"from": owner})
    with reverts("MARKET_PAUSED"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID))


def test_create_evm_script(owner, core_stub, adaptive_curve_irm_stub, market_params, factory):
    "Must accrue interest before applying the new IRM config"
    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID))

    expected_evm_script = encode_call_script(
        [
            (
                core_stub.address,
                core_stub.accrueInterest.encode_input(market_params),
            ),
            (
                adaptive_curve_irm_stub.address,
                adaptive_curve_irm_stub.applyIrmConfig.encode_input(market_params, IRM_CONFIG),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_config = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_config == IRM_CONFIG
