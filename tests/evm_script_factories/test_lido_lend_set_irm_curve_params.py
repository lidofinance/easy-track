import pytest
from eth_abi import encode
from brownie import reverts, LidoLendSetIrmCurveParams, LidoLendCoreStub, IrmRouterStub, AdaptiveCurveIrmStub

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")

LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
LLTV = 800000000000000000

from utils.lido_lend import CURVE_PARAMS_ABI_TYPE as CURVE_PARAMS_TYPE

WAD = 10**18
MAX_ADJUSTMENT_SPEED = 10_000 * WAD // (365 * 24 * 60 * 60)
MAX_RATE_AT_TARGET = 10_000 * WAD // (365 * 24 * 60 * 60)
MAX_BORROW_RATE = MAX_RATE_AT_TARGET * 100
NEW_CURVE_PARAMS = (
    4 * WAD,
    1_585_489_599_188,
    90 * 10**16,
    1_268_391_679,
    31_709_791,
    63_419_583_967,
    0,
)


def create_calldata(market_id, curve_params):
    return "0x" + encode(["bytes32", CURVE_PARAMS_TYPE], [market_id, curve_params]).hex()


@pytest.fixture(scope="module")
def router_stub(owner):
    return IrmRouterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def curve_stub(owner):
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
def factory(owner, core_stub, router_stub, curve_stub):
    return LidoLendSetIrmCurveParams.deploy(owner, core_stub, router_stub, curve_stub, {"from": owner})


def test_deploy(owner, core_stub, router_stub, curve_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub
    assert factory.irmRouter() == router_stub
    assert factory.adaptiveCurveIrm() == curve_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_CURVE_PARAMS))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the market was never created on the core (no params.irm)"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_CURVE_PARAMS))


def test_create_evm_script_irm_not_router(owner, core_stub, factory):
    "Must reject a market whose id commits to an IRM other than the configured domain router"
    foreign_router = IrmRouterStub.deploy({"from": owner})
    foreign_market_id = (3).to_bytes(32, "big")
    foreign_params = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, foreign_router.address, LLTV)
    core_stub.setMarketParams(foreign_market_id, foreign_params, {"from": owner})

    with reverts("IRM_NOT_ROUTER"):
        factory.createEVMScript(owner, create_calldata(foreign_market_id, NEW_CURVE_PARAMS))


def _with_curve_param(index, value):
    params = list(NEW_CURVE_PARAMS)
    params[index] = value
    return tuple(params)


@pytest.mark.parametrize(
    "curve_params,error",
    [
        (_with_curve_param(0, WAD - 1), "invalid curveSteepness"),
        (_with_curve_param(0, 100 * WAD + 1), "invalid curveSteepness"),
        (_with_curve_param(1, -1), "invalid adjustmentSpeed"),
        (_with_curve_param(1, MAX_ADJUSTMENT_SPEED + 1), "invalid adjustmentSpeed"),
        (_with_curve_param(2, 0), "invalid targetUtilization"),
        (_with_curve_param(2, WAD), "invalid targetUtilization"),
        (_with_curve_param(4, 0), "invalid rate bounds"),
        (_with_curve_param(5, NEW_CURVE_PARAMS[4] - 1), "invalid rate bounds"),
        (_with_curve_param(5, MAX_RATE_AT_TARGET + 1), "invalid rate bounds"),
        (_with_curve_param(3, NEW_CURVE_PARAMS[4] - 1), "invalid initialRateAtTarget"),
        (_with_curve_param(3, NEW_CURVE_PARAMS[5] + 1), "invalid initialRateAtTarget"),
        (_with_curve_param(6, MAX_BORROW_RATE + 1), "invalid maxBorrowRate"),
    ],
)
def test_create_evm_script_invalid_curve_params(owner, factory, curve_params, error):
    "Must reject every curve configuration that AdaptiveCurveIrm would reject when enacted"
    with reverts(error):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, curve_params))


def test_create_evm_script(owner, curve_stub, market_params, factory):
    "Must create correct EVMScript targeting the configured AdaptiveCurveIrm singleton"
    calldata = create_calldata(MARKET_ID, NEW_CURVE_PARAMS)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                curve_stub.address,
                curve_stub.setMarketCurveParams.encode_input(market_params, NEW_CURVE_PARAMS),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_params = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, NEW_CURVE_PARAMS))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_params == NEW_CURVE_PARAMS


def test_target_is_the_adaptive_curve_singleton_regardless_of_market_id(owner):
    "Every supported market uses the same static target; the market id only changes the payload."
    router = IrmRouterStub.deploy({"from": owner})
    mp_a = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router.address, LLTV)
    mp_b = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router.address, LLTV + 1)
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (1).to_bytes(32, "big"), (2).to_bytes(32, "big")
    curve = AdaptiveCurveIrmStub.deploy({"from": owner})
    core.setMarketParams(market_a, mp_a, {"from": owner})
    core.setMarketParams(market_b, mp_b, {"from": owner})

    factory = LidoLendSetIrmCurveParams.deploy(owner, core, router, curve, {"from": owner})
    script_a = factory.createEVMScript(owner, create_calldata(market_a, NEW_CURVE_PARAMS))
    script_b = factory.createEVMScript(owner, create_calldata(market_b, NEW_CURVE_PARAMS))

    assert script_a == encode_call_script(
        [(curve.address, curve.setMarketCurveParams.encode_input(mp_a, NEW_CURVE_PARAMS))]
    )
    assert script_b == encode_call_script(
        [(curve.address, curve.setMarketCurveParams.encode_input(mp_b, NEW_CURVE_PARAMS))]
    )
    assert script_a != script_b
