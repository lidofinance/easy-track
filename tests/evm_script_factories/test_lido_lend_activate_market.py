import pytest
from eth_abi import encode
from eth_utils import keccak
from brownie import (
    reverts,
    ZERO_ADDRESS,
    LidoLendActivateMarket,
    LidoLendOwnerStub,
    IrmRouterStub,
    CircuitBreakerStub,
    LidoLendMarketControllerStub,
)

from utils.evm_script import encode_call_script

MP_TYPE = "(address,address,address,address,uint256)"
ACTIVATE_TYPES = [MP_TYPE, "address", "address", "address", "bool"]

LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
IRM = f"0x{4:040x}"
LLTV = 800000000000000000
WAD = 10**18
CURVE = f"0x{5:040x}"
CONTROLLER = f"0x{6:040x}"
PAUSER_COMMITTEE = f"0x{7:040x}"

MARKET_PARAMS = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, IRM, LLTV)
MARKET_ID = keccak(encode([MP_TYPE], [MARKET_PARAMS]))


def create_calldata(market_params, curve, controller, pauser_committee, enable_settlement):
    return "0x" + encode(ACTIVATE_TYPES, [market_params, curve, controller, pauser_committee, enable_settlement]).hex()


@pytest.fixture(scope="module")
def owner_stub(owner):
    return LidoLendOwnerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def irm_router_stub(owner):
    return IrmRouterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def circuit_breaker_stub(owner):
    return CircuitBreakerStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def controller(owner):
    "A controller whose marketId matches MARKET_PARAMS (so the factory's cross-check passes)."
    c = LidoLendMarketControllerStub.deploy({"from": owner})
    c.setMarketId(MARKET_ID, {"from": owner})
    return c


@pytest.fixture(scope="module")
def factory(owner, owner_stub, irm_router_stub, circuit_breaker_stub):
    return LidoLendActivateMarket.deploy(
        owner,
        owner_stub,
        irm_router_stub,
        circuit_breaker_stub,
        {"from": owner},
    )


def test_deploy(owner, owner_stub, irm_router_stub, circuit_breaker_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_stub
    assert factory.irmRouter() == irm_router_stub
    assert factory.circuitBreaker() == circuit_breaker_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    calldata = create_calldata(MARKET_PARAMS, CURVE, CONTROLLER, PAUSER_COMMITTEE, False)
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata)


@pytest.mark.parametrize(
    "market_params,curve,controller,pauser,error",
    [
        ((ZERO_ADDRESS, COLLATERAL_TOKEN, ORACLE, IRM, LLTV), CURVE, CONTROLLER, PAUSER_COMMITTEE, "ZERO_LOAN_TOKEN"),
        ((LOAN_TOKEN, ZERO_ADDRESS, ORACLE, IRM, LLTV), CURVE, CONTROLLER, PAUSER_COMMITTEE, "ZERO_COLLATERAL_TOKEN"),
        ((LOAN_TOKEN, COLLATERAL_TOKEN, ZERO_ADDRESS, IRM, LLTV), CURVE, CONTROLLER, PAUSER_COMMITTEE, "ZERO_ORACLE"),
        ((LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, ZERO_ADDRESS, LLTV), CURVE, CONTROLLER, PAUSER_COMMITTEE, "ZERO_IRM"),
        (MARKET_PARAMS, ZERO_ADDRESS, CONTROLLER, PAUSER_COMMITTEE, "ZERO_CURVE"),
        (MARKET_PARAMS, CURVE, ZERO_ADDRESS, PAUSER_COMMITTEE, "ZERO_CONTROLLER"),
        (MARKET_PARAMS, CURVE, CONTROLLER, ZERO_ADDRESS, "ZERO_PAUSER_COMMITTEE"),
    ],
)
def test_create_evm_script_zero_address(owner, factory, market_params, curve, controller, pauser, error):
    "Must revert with the matching ZERO_* message if any required address is the zero address"
    calldata = create_calldata(market_params, curve, controller, pauser, False)
    with reverts(error):
        factory.createEVMScript(owner, calldata)


def test_create_evm_script_max_lltv(owner, factory, controller):
    "Must revert with 'MAX_LLTV_EXCEEDED' if lltv is >= WAD (the core caps it at market creation)"
    market_params = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, IRM, WAD)
    with reverts("MAX_LLTV_EXCEEDED"):
        factory.createEVMScript(owner, create_calldata(market_params, CURVE, controller.address, PAUSER_COMMITTEE, False))


def test_create_evm_script_controller_mismatch(owner, factory):
    "Must revert with 'CONTROLLER_MISMATCH' if the controller does not belong to the market"
    other = LidoLendMarketControllerStub.deploy({"from": owner})
    other.setMarketId(keccak(b"other"), {"from": owner})
    with reverts("CONTROLLER_MISMATCH"):
        factory.createEVMScript(owner, create_calldata(MARKET_PARAMS, CURVE, other.address, PAUSER_COMMITTEE, False))


@pytest.mark.parametrize("enable_settlement", [False, True])
def test_create_evm_script(owner, owner_stub, irm_router_stub, circuit_breaker_stub, controller, factory, enable_settlement):
    "Must create the three activation calls in order, forwarding enableSettlement to createMarket"
    calldata = create_calldata(MARKET_PARAMS, CURVE, controller.address, PAUSER_COMMITTEE, enable_settlement)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                irm_router_stub.address,
                irm_router_stub.setMarketIrm.encode_input(MARKET_PARAMS, CURVE),
            ),
            (
                owner_stub.address,
                owner_stub.createMarket.encode_input(MARKET_PARAMS, controller.address, enable_settlement),
            ),
            (
                circuit_breaker_stub.address,
                circuit_breaker_stub.registerPauser.encode_input(controller.address, PAUSER_COMMITTEE),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_PARAMS, CURVE, CONTROLLER, PAUSER_COMMITTEE, True)
    decoded = factory.decodeEVMScriptCallData(calldata)
    market_params, curve, controller, pauser, enable_settlement = decoded
    assert market_params == MARKET_PARAMS
    assert curve == CURVE
    assert controller == CONTROLLER
    assert pauser == PAUSER_COMMITTEE
    assert enable_settlement is True
