import pytest
from eth_abi import encode
from brownie import reverts, LidoLendSetIrmCurveParams, LidoLendCoreStub, IrmRouterStub, AdaptiveCurveIrmStub

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
CURVE_UNSET_MARKET_ID = (3).to_bytes(32, "big")

LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
LLTV = 800000000000000000

from utils.lido_lend import CURVE_PARAMS_ABI_TYPE as CURVE_PARAMS_TYPE
NEW_CURVE_PARAMS = (
    4 * 10**18,
    50 * 10**16,
    90 * 10**16,
    4 * 10**16 // (365 * 24 * 3600),
    1 * 10**15 // (365 * 24 * 3600),
    2 * 10**18 // (365 * 24 * 3600),
    10**18,
)
MIN_RATE = 1 * 10**15 // (365 * 24 * 3600)
MAX_RATE = 2 * 10**18 // (365 * 24 * 3600)


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
def core_stub(owner, market_params, router_stub, curve_stub):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketParams(MARKET_ID, market_params, {"from": owner})
    core.setMarketParams(CURVE_UNSET_MARKET_ID, market_params, {"from": owner})
    router_stub.setMarketCurve(MARKET_ID, curve_stub, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub):
    return LidoLendSetIrmCurveParams.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, NEW_CURVE_PARAMS))


def _mut(idx, val):
    t = list(NEW_CURVE_PARAMS)
    t[idx] = val
    return tuple(t)


@pytest.mark.parametrize(
    "params,error",
    [
        (_mut(1, -1), "INVALID_ADJUSTMENT_SPEED"),
        (_mut(2, 0), "INVALID_TARGET_UTILIZATION"),
        (_mut(4, 0), "INVALID_RATE_BOUNDS"),
        (_mut(5, MIN_RATE - 1), "INVALID_RATE_BOUNDS"),
        (_mut(3, MIN_RATE - 1), "INVALID_INITIAL_RATE"),
        (_mut(3, MAX_RATE + 1), "INVALID_INITIAL_RATE"),
    ],
)
def test_create_evm_script_malformed_params(owner, factory, params, error):
    "Must reject malformed curve params at creation (mirrors AdaptiveCurveConfig's relational invariants)"
    with reverts(error):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, params))


def test_create_evm_script_market_not_found(owner, factory):
    "Must revert with 'MARKET_NOT_FOUND' if the market was never created on the core (no params.irm)"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, NEW_CURVE_PARAMS))


def test_create_evm_script_curve_not_found(owner, factory):
    "Must revert with 'CURVE_NOT_FOUND' if the market exists but the router routes it to no curve"
    with reverts("CURVE_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(CURVE_UNSET_MARKET_ID, NEW_CURVE_PARAMS))


def test_create_evm_script(owner, curve_stub, market_params, factory):
    "Must create correct EVMScript targeting the market's curve when all requirements are met"
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


def test_resolves_curve_per_market_id(owner):
    "The target curve is resolved from the calldata marketId via core -> router.marketIrm(id), so one factory reparametrizes each market's own curve."
    router = IrmRouterStub.deploy({"from": owner})
    mp = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router.address, LLTV)
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (1).to_bytes(32, "big"), (2).to_bytes(32, "big")
    curve_a = AdaptiveCurveIrmStub.deploy({"from": owner})
    curve_b = AdaptiveCurveIrmStub.deploy({"from": owner})
    for mid, curve in ((market_a, curve_a), (market_b, curve_b)):
        core.setMarketParams(mid, mp, {"from": owner})
        router.setMarketCurve(mid, curve, {"from": owner})

    factory = LidoLendSetIrmCurveParams.deploy(owner, core, {"from": owner})
    script_a = factory.createEVMScript(owner, create_calldata(market_a, NEW_CURVE_PARAMS))
    script_b = factory.createEVMScript(owner, create_calldata(market_b, NEW_CURVE_PARAMS))

    assert script_a == encode_call_script(
        [(curve_a.address, curve_a.setMarketCurveParams.encode_input(mp, NEW_CURVE_PARAMS))]
    )
    assert script_b == encode_call_script(
        [(curve_b.address, curve_b.setMarketCurveParams.encode_input(mp, NEW_CURVE_PARAMS))]
    )
    assert script_a != script_b
