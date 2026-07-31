from brownie import LidoLendSetIrmConfig, LidoLendCoreStub, IrmRouterStub, AdaptiveCurveIrmStub, reverts
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
def core_stub(owner, market_params):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketParams(MARKET_ID, market_params, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub, router_stub, adaptive_curve_irm_stub):
    return LidoLendSetIrmConfig.deploy(
        owner,
        core_stub,
        router_stub,
        adaptive_curve_irm_stub,
        {"from": owner},
    )


def test_deploy(owner, core_stub, router_stub, adaptive_curve_irm_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub
    assert factory.irmRouter() == router_stub
    assert factory.adaptiveCurveIrm() == adaptive_curve_irm_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID))


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


def test_create_evm_script(owner, adaptive_curve_irm_stub, market_params, factory):
    "Must create correct EVMScript targeting the configured AdaptiveCurveIrm singleton"
    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID))

    expected_evm_script = encode_call_script(
        [
            (
                adaptive_curve_irm_stub.address,
                adaptive_curve_irm_stub.applyIrmConfig.encode_input(market_params, IRM_CONFIG),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_config = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_config == IRM_CONFIG


def test_target_is_the_adaptive_curve_singleton_regardless_of_market_id(owner):
    "Every supported market uses the same static target; the market id only changes the payload."
    router = IrmRouterStub.deploy({"from": owner})
    mp_a = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router.address, LLTV)
    mp_b = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router.address, LLTV + 1)
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (1).to_bytes(32, "big"), (2).to_bytes(32, "big")
    adaptive = AdaptiveCurveIrmStub.deploy({"from": owner})
    core.setMarketParams(market_a, mp_a, {"from": owner})
    core.setMarketParams(market_b, mp_b, {"from": owner})

    factory = LidoLendSetIrmConfig.deploy(owner, core, router, adaptive, {"from": owner})
    script_a = factory.createEVMScript(owner, create_calldata(market_a))
    script_b = factory.createEVMScript(owner, create_calldata(market_b))

    assert script_a == encode_call_script([(adaptive.address, adaptive.applyIrmConfig.encode_input(mp_a, IRM_CONFIG))])
    assert script_b == encode_call_script([(adaptive.address, adaptive.applyIrmConfig.encode_input(mp_b, IRM_CONFIG))])
    assert script_a != script_b
