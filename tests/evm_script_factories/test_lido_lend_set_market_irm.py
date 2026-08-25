import pytest
from eth_abi import encode
from brownie import (
    AdaptiveCurveIrmStub,
    reverts,
    LidoLendIrmActions,
    LidoLendCoreStub,
    IrmRouterStub,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
LLTV = 800000000000000000
EOA = "0x" + "ee" * 20
SET_MARKET_IRM = 1


def create_payload(market_id, irm):
    return encode(["bytes32", "address"], [market_id, str(irm)])


def create_calldata(market_id, irm):
    return (
        "0x"
        + encode(
            ["uint8", "bytes"],
            [SET_MARKET_IRM, create_payload(market_id, irm)],
        ).hex()
    )


@pytest.fixture(scope="module")
def router_stub(owner):
    return IrmRouterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def market_params(router_stub):
    return (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router_stub.address, LLTV)


@pytest.fixture(scope="module")
def new_irm(owner):
    return AdaptiveCurveIrmStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def adaptive_curve_irm(owner):
    return AdaptiveCurveIrmStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, market_params):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketParams(MARKET_ID, market_params, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub, router_stub, adaptive_curve_irm):
    return LidoLendIrmActions.deploy(owner, core_stub, router_stub, adaptive_curve_irm, {"from": owner})


def test_create_evm_script_zero_irm(owner, factory):
    "Must reject the zero IRM when the motion is created"
    with reverts("ZERO_IRM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS))


def test_create_evm_script_does_not_validate_irm(owner, router_stub, market_params, factory):
    "Must leave selected-IRM validation to governance and the router"
    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, EOA))

    assert evm_script == encode_call_script(
        [(router_stub.address, router_stub.setMarketIrm.encode_input(market_params, EOA))]
    )


def test_create_evm_script_market_not_found(owner, factory, new_irm):
    "Must revert with 'MARKET_NOT_FOUND' if the market was never created on the core (no params.irm)"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, new_irm))


def test_create_evm_script_irm_not_router(owner, core_stub, factory, new_irm):
    "Must reject a market whose id commits to an IRM other than the configured domain router"
    foreign_router = IrmRouterStub.deploy({"from": owner})
    foreign_market_id = (3).to_bytes(32, "big")
    foreign_params = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, foreign_router.address, LLTV)
    core_stub.setMarketParams(foreign_market_id, foreign_params, {"from": owner})

    with reverts("IRM_NOT_ROUTER"):
        factory.createEVMScript(owner, create_calldata(foreign_market_id, new_irm))


def test_create_evm_script(owner, router_stub, market_params, new_irm, factory):
    "Must create correct EVMScript targeting the market's router when the new IRM is a non-zero contract"
    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, new_irm))
    expected_evm_script = encode_call_script(
        [(router_stub.address, router_stub.setMarketIrm.encode_input(market_params, new_irm))]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, new_irm):
    "Must decode EVMScript call data correctly"
    action, payload = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, new_irm))
    assert action == SET_MARKET_IRM
    decoded_market_id, decoded_irm = factory.decodeSetMarketIrmPayload(payload)
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_irm == new_irm
