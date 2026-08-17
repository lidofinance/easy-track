import pytest
from eth_abi import encode
from eth_utils import keccak
from brownie import (
    reverts,
    ZERO_ADDRESS,
    LidoLendActivateMarket,
    LidoLendCoreStub,
    LidoLendOwnerStub,
    IrmRouterStub,
    AdaptiveCurveIrmStub,
    CircuitBreakerStub,
    LidoLendMarketControllerStub,
    RiskStewardDashboardStub,
)

from utils.evm_script import encode_call_script

from utils.lido_lend import MARKET_PARAMS_ABI_TYPE as MP_TYPE

ACTIVATE_TYPES = [MP_TYPE, "address", "address", "address", "address", "bool"]

LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
IRM = f"0x{4:040x}"
LLTV = 800000000000000000
WAD = 10**18
IRM_CONFIG = f"0x{5:040x}"
CONTROLLER = f"0x{6:040x}"
PAUSER_COMMITTEE = f"0x{7:040x}"
STEWARD = f"0x{8:040x}"

# Placeholder params for checks that revert BEFORE the "irm is the router" check (irm value irrelevant there).
MARKET_PARAMS = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, IRM, LLTV)


def create_calldata(market_params, irm_config, controller, steward, pauser_committee, enable_settlement):
    return (
        "0x"
        + encode(
            ACTIVATE_TYPES,
            [market_params, irm_config, controller, steward, pauser_committee, enable_settlement],
        ).hex()
    )


@pytest.fixture(scope="module")
def core_stub(owner):
    return LidoLendCoreStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def owner_stub(owner, core_stub):
    owner_facade = LidoLendOwnerStub.deploy({"from": owner})
    owner_facade.setCore(core_stub, {"from": owner})
    return owner_facade


@pytest.fixture(scope="module")
def irm_router_stub(owner):
    return IrmRouterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def adaptive_curve_irm_stub(owner):
    return AdaptiveCurveIrmStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def circuit_breaker_stub(owner):
    return CircuitBreakerStub.deploy(owner, {"from": owner})


@pytest.fixture(scope="module")
def risk_steward_dashboard_stub(owner):
    return RiskStewardDashboardStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def market_params(irm_router_stub):
    "Market params whose irm is the domain router — required by the factory's IRM_NOT_ROUTER check."
    return (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, irm_router_stub.address, LLTV)


@pytest.fixture(scope="module")
def market_id(market_params):
    return keccak(encode([MP_TYPE], [market_params]))


@pytest.fixture(scope="module")
def controller(owner, market_id, circuit_breaker_stub):
    "A controller whose marketId matches market_params (so the factory's cross-check passes)."
    c = LidoLendMarketControllerStub.deploy({"from": owner})
    c.setMarketId(market_id, {"from": owner})
    c.grantRole(c.PAUSER_ROLE(), circuit_breaker_stub, {"from": owner})
    return c


@pytest.fixture(scope="module")
def factory(
    owner,
    owner_stub,
    irm_router_stub,
    adaptive_curve_irm_stub,
    circuit_breaker_stub,
    risk_steward_dashboard_stub,
):
    return LidoLendActivateMarket.deploy(
        owner,
        owner_stub,
        irm_router_stub,
        adaptive_curve_irm_stub,
        circuit_breaker_stub,
        risk_steward_dashboard_stub,
        {"from": owner},
    )


def test_deploy(
    owner,
    owner_stub,
    irm_router_stub,
    adaptive_curve_irm_stub,
    circuit_breaker_stub,
    risk_steward_dashboard_stub,
    factory,
):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_stub
    assert factory.irmRouter() == irm_router_stub
    assert factory.adaptiveCurveIrm() == adaptive_curve_irm_stub
    assert factory.circuitBreaker() == circuit_breaker_stub
    assert factory.riskStewardDashboard() == risk_steward_dashboard_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    calldata = create_calldata(MARKET_PARAMS, IRM_CONFIG, CONTROLLER, STEWARD, PAUSER_COMMITTEE, False)
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata)


@pytest.mark.parametrize(
    "market_params,irm_config,controller,steward,pauser,error",
    [
        (
            (ZERO_ADDRESS, COLLATERAL_TOKEN, ORACLE, IRM, LLTV),
            IRM_CONFIG,
            CONTROLLER,
            STEWARD,
            PAUSER_COMMITTEE,
            "ZERO_LOAN_TOKEN",
        ),
        (
            (LOAN_TOKEN, ZERO_ADDRESS, ORACLE, IRM, LLTV),
            IRM_CONFIG,
            CONTROLLER,
            STEWARD,
            PAUSER_COMMITTEE,
            "ZERO_COLLATERAL_TOKEN",
        ),
        (
            (LOAN_TOKEN, COLLATERAL_TOKEN, ZERO_ADDRESS, IRM, LLTV),
            IRM_CONFIG,
            CONTROLLER,
            STEWARD,
            PAUSER_COMMITTEE,
            "ZERO_ORACLE",
        ),
        (MARKET_PARAMS, IRM_CONFIG, ZERO_ADDRESS, STEWARD, PAUSER_COMMITTEE, "ZERO_CONTROLLER"),
        (MARKET_PARAMS, IRM_CONFIG, CONTROLLER, ZERO_ADDRESS, PAUSER_COMMITTEE, "ZERO_STEWARD"),
        (MARKET_PARAMS, IRM_CONFIG, CONTROLLER, STEWARD, ZERO_ADDRESS, "ZERO_PAUSER_COMMITTEE"),
    ],
)
def test_create_evm_script_zero_address(owner, factory, market_params, irm_config, controller, steward, pauser, error):
    "Must revert with the matching ZERO_* message if any required address is the zero address"
    calldata = create_calldata(market_params, irm_config, controller, steward, pauser, False)
    with reverts(error):
        factory.createEVMScript(owner, calldata)


def test_create_evm_script_irm_not_router(owner, factory, controller):
    "Must revert with 'IRM_NOT_ROUTER' if market params do not point at the domain router"
    market_params = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, f"0x{123:040x}", LLTV)
    with reverts("IRM_NOT_ROUTER"):
        factory.createEVMScript(
            owner, create_calldata(market_params, IRM_CONFIG, controller.address, STEWARD, PAUSER_COMMITTEE, False)
        )


def test_create_evm_script_market_already_created(owner, core_stub, factory, market_id, market_params, controller):
    "Must revert if a market with the given params is already created"
    core_stub.activateMarket(market_id, market_params, False, {"from": owner})

    with reverts("MARKET_ALREADY_CREATED"):
        factory.createEVMScript(
            owner,
            create_calldata(market_params, IRM_CONFIG, controller.address, STEWARD, PAUSER_COMMITTEE, False),
        )


def test_create_evm_script_max_lltv(owner, factory, controller):
    "Must revert with 'MAX_LLTV_EXCEEDED' if lltv is >= WAD (the core caps it at market creation)"
    market_params = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, IRM, WAD)
    with reverts("MAX_LLTV_EXCEEDED"):
        factory.createEVMScript(
            owner, create_calldata(market_params, IRM_CONFIG, controller.address, STEWARD, PAUSER_COMMITTEE, False)
        )


def test_create_evm_script_controller_mismatch(owner, factory, market_params):
    "Must revert with 'CONTROLLER_MISMATCH' if the controller does not belong to the market"
    other = LidoLendMarketControllerStub.deploy({"from": owner})
    other.setMarketId(keccak(b"other"), {"from": owner})
    with reverts("CONTROLLER_MISMATCH"):
        factory.createEVMScript(
            owner, create_calldata(market_params, IRM_CONFIG, other.address, STEWARD, PAUSER_COMMITTEE, False)
        )


def test_create_evm_script_circuit_breaker_without_pauser_role(
    owner,
    LidoLendActivateMarket,
    CircuitBreakerStub,
    owner_stub,
    irm_router_stub,
    adaptive_curve_irm_stub,
    circuit_breaker_stub,
    risk_steward_dashboard_stub,
    controller,
    market_params,
):
    "Must reject a CircuitBreaker with the right ADMIN but no PAUSER_ROLE on the controller."
    wrong_circuit_breaker = CircuitBreakerStub.deploy(circuit_breaker_stub.ADMIN(), {"from": owner})
    factory = LidoLendActivateMarket.deploy(
        owner,
        owner_stub,
        irm_router_stub,
        adaptive_curve_irm_stub,
        wrong_circuit_breaker,
        risk_steward_dashboard_stub,
        {"from": owner},
    )

    with reverts("CIRCUIT_BREAKER_NOT_PAUSER"):
        factory.createEVMScript(
            owner,
            create_calldata(market_params, IRM_CONFIG, controller.address, STEWARD, PAUSER_COMMITTEE, False),
        )


@pytest.mark.parametrize("enable_settlement", [False, True])
def test_create_evm_script(
    owner,
    owner_stub,
    irm_router_stub,
    adaptive_curve_irm_stub,
    circuit_breaker_stub,
    risk_steward_dashboard_stub,
    controller,
    market_id,
    market_params,
    factory,
    enable_settlement,
):
    "Must create the five activation calls in order, including the independently supplied market steward"
    calldata = create_calldata(
        market_params,
        IRM_CONFIG,
        controller.address,
        STEWARD,
        PAUSER_COMMITTEE,
        enable_settlement,
    )
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                adaptive_curve_irm_stub.address,
                adaptive_curve_irm_stub.applyIrmConfig.encode_input(market_params, IRM_CONFIG),
            ),
            (
                irm_router_stub.address,
                irm_router_stub.setMarketIrm.encode_input(market_params, adaptive_curve_irm_stub.address),
            ),
            (
                owner_stub.address,
                owner_stub.createMarket.encode_input(market_params, controller.address, enable_settlement),
            ),
            (
                risk_steward_dashboard_stub.address,
                risk_steward_dashboard_stub.addMarketSteward.encode_input(market_id, STEWARD),
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
    calldata = create_calldata(MARKET_PARAMS, IRM_CONFIG, CONTROLLER, STEWARD, PAUSER_COMMITTEE, True)
    decoded = factory.decodeEVMScriptCallData(calldata)
    market_params, irm_config, controller, steward, pauser, enable_settlement = decoded
    assert market_params == MARKET_PARAMS
    assert irm_config == IRM_CONFIG
    assert controller == CONTROLLER
    assert steward == STEWARD
    assert pauser == PAUSER_COMMITTEE
    assert enable_settlement is True
