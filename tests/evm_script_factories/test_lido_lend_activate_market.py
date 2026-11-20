import pytest
from eth_abi import encode
from eth_utils import keccak
from brownie import (
    reverts,
    ZERO_ADDRESS,
    LidoLendActivateMarket,
    LidoLendCoreStub,
    LidoLendPreseeder,
    LidoLendVaultStub,
    LidoLendOwnerStub,
    IrmRouterStub,
    AdaptiveCurveIrmStub,
    CircuitBreakerStub,
    LidoLendMarketFactoryStub,
    LidoLendMarketControllerStub,
    MockERC20,
    RiskStewardDashboardStub,
)

from utils.evm_script import encode_call_script

from utils.lido_lend import MARKET_PARAMS_ABI_TYPE as MP_TYPE

ACTIVATION_PARAMS_TYPE = f"({MP_TYPE},address,address,bool,address,address,address,uint256)"

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
VAULT = f"0x{9:040x}"
GUARDIAN_SIGNALS = f"0x{10:040x}"
INITIAL_FEE = 10**17
MAX_FEE = 25 * 10**16

# Placeholder params for checks that revert BEFORE the "irm is the router" check (irm value irrelevant there).
MARKET_PARAMS = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, IRM, LLTV)


def create_calldata(
    market_params,
    irm_config,
    controller,
    steward,
    pauser_committee,
    enable_settlement,
    fee=INITIAL_FEE,
    vault=VAULT,
):
    return (
        "0x"
        + encode(
            [ACTIVATION_PARAMS_TYPE],
            [
                (
                    market_params,
                    irm_config,
                    controller,
                    enable_settlement,
                    steward,
                    pauser_committee,
                    vault,
                    fee,
                )
            ],
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
def preseeder(owner, core_stub, loan_token):
    "Deployed funded: createEVMScript validates the preseeder balance via validatePreseed."
    preseeder = LidoLendPreseeder.deploy(core_stub, owner, owner, {"from": owner})
    loan_token.mint(preseeder, 10**12, {"from": owner})
    return preseeder


@pytest.fixture(scope="module")
def loan_token(owner):
    return MockERC20.deploy(18, {"from": owner})


@pytest.fixture(scope="module")
def vault_stub(owner, loan_token, core_stub, market_id):
    "A vault wired to the descriptor market (so the factory's preseeder-parity checks pass)."
    vault = LidoLendVaultStub.deploy({"from": owner})
    vault.setAsset(loan_token, {"from": owner})
    vault.setLidoLend(core_stub, {"from": owner})
    vault.setMarketId(market_id, {"from": owner})
    return vault


@pytest.fixture(scope="module")
def market_params(irm_router_stub, loan_token):
    "Market params whose irm is the domain router — required by the factory's IRM_NOT_ROUTER check."
    return (loan_token.address, COLLATERAL_TOKEN, ORACLE, irm_router_stub.address, LLTV)


@pytest.fixture(scope="module")
def market_id(market_params):
    return keccak(encode([MP_TYPE], [market_params]))


@pytest.fixture(scope="module")
def controller(
    owner,
    core_stub,
    market_id,
    circuit_breaker_stub,
    owner_stub,
    risk_steward_dashboard_stub,
):
    "A controller whose marketId matches market_params (so the factory's cross-check passes)."
    c = LidoLendMarketControllerStub.deploy({"from": owner})
    c.setLidoLend(core_stub, {"from": owner})
    c.setMarketId(market_id, {"from": owner})
    c.setGuardianSignals(GUARDIAN_SIGNALS, {"from": owner})
    c.grantRole(c.MANAGER_ROLE(), owner_stub, {"from": owner})
    c.grantRole(c.MANAGER_ROLE(), risk_steward_dashboard_stub, {"from": owner})
    c.grantRole(c.UNFREEZER_ROLE(), owner_stub, {"from": owner})
    c.grantRole(c.FREEZER_ROLE(), risk_steward_dashboard_stub, {"from": owner})
    c.grantRole(c.PAUSER_ROLE(), circuit_breaker_stub, {"from": owner})
    return c


@pytest.fixture(scope="module")
def market_factory_stub(owner, controller, market_id, market_params, vault_stub):
    market_factory = LidoLendMarketFactoryStub.deploy({"from": owner})
    market_factory.setExpectedValidation(
        controller,
        market_id,
        GUARDIAN_SIGNALS,
        vault_stub,
        market_params,
        {"from": owner},
    )
    return market_factory


@pytest.fixture(scope="module")
def factory(
    owner,
    owner_stub,
    irm_router_stub,
    adaptive_curve_irm_stub,
    market_factory_stub,
    circuit_breaker_stub,
    risk_steward_dashboard_stub,
    preseeder,
):
    return LidoLendActivateMarket.deploy(
        owner,
        owner_stub,
        irm_router_stub,
        adaptive_curve_irm_stub,
        market_factory_stub,
        circuit_breaker_stub,
        risk_steward_dashboard_stub,
        preseeder,
        {"from": owner},
    )


def test_configurable_irm(factory, adaptive_curve_irm_stub):
    assert factory.configurableIrm() == adaptive_curve_irm_stub


def test_lido_lend_market_factory(factory, market_factory_stub):
    assert factory.lidoLendMarketFactory() == market_factory_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    calldata = create_calldata(MARKET_PARAMS, IRM_CONFIG, CONTROLLER, STEWARD, PAUSER_COMMITTEE, False)
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata)


@pytest.mark.parametrize(
    "invalid_market_params,irm_config,controller_address,steward,pauser,error",
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
        (MARKET_PARAMS, ZERO_ADDRESS, CONTROLLER, STEWARD, PAUSER_COMMITTEE, "ZERO_IRM_CONFIG"),
        (MARKET_PARAMS, IRM_CONFIG, ZERO_ADDRESS, STEWARD, PAUSER_COMMITTEE, "ZERO_CONTROLLER"),
        (MARKET_PARAMS, IRM_CONFIG, CONTROLLER, ZERO_ADDRESS, PAUSER_COMMITTEE, "ZERO_STEWARD"),
        (MARKET_PARAMS, IRM_CONFIG, CONTROLLER, STEWARD, ZERO_ADDRESS, "ZERO_PAUSER_COMMITTEE"),
    ],
)
def test_create_evm_script_zero_address(
    owner, factory, invalid_market_params, irm_config, controller_address, steward, pauser, error
):
    "Must revert with the matching ZERO_* message if any required address is the zero address"
    calldata = create_calldata(invalid_market_params, irm_config, controller_address, steward, pauser, False)
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


def test_create_evm_script_max_fee(owner, factory, market_params, controller):
    "Must reject an initial fee above the core's 25% cap"
    with reverts("MAX_FEE_EXCEEDED"):
        factory.createEVMScript(
            owner,
            create_calldata(
                market_params,
                IRM_CONFIG,
                controller.address,
                STEWARD,
                PAUSER_COMMITTEE,
                False,
                MAX_FEE + 1,
            ),
        )


def test_create_evm_script_zero_vault(owner, factory, market_params, controller):
    with reverts("ZERO_VAULT"):
        factory.createEVMScript(
            owner,
            create_calldata(
                market_params,
                IRM_CONFIG,
                controller.address,
                STEWARD,
                PAUSER_COMMITTEE,
                False,
                vault=ZERO_ADDRESS,
            ),
        )


@pytest.mark.parametrize(
    "misconfigure,error",
    [
        ("wrong_core", "LIDO_LEND_MISMATCH"),
        ("wrong_market", "MARKET_ID_MISMATCH"),
        ("wrong_asset", "VAULT_ASSET_MISMATCH"),
        ("non_empty", "VAULT_NOT_EMPTY"),
    ],
)
def test_create_evm_script_rejects_vault_failing_preseeder_checks(
    owner, factory, core_stub, market_id, market_params, controller, loan_token, misconfigure, error
):
    "Must mirror the preseeder validation: the vault wraps this market, core, and loan token, and is empty"
    vault = LidoLendVaultStub.deploy({"from": owner})
    vault.setAsset(loan_token, {"from": owner})
    vault.setLidoLend(core_stub, {"from": owner})
    vault.setMarketId(market_id, {"from": owner})

    if misconfigure == "wrong_core":
        vault.setLidoLend(LidoLendCoreStub.deploy({"from": owner}), {"from": owner})
    elif misconfigure == "wrong_market":
        vault.setMarketId(keccak(b"other"), {"from": owner})
    elif misconfigure == "wrong_asset":
        vault.setAsset(MockERC20.deploy(18, {"from": owner}), {"from": owner})
    else:
        loan_token.mint(owner, 1, {"from": owner})
        loan_token.approve(vault, 1, {"from": owner})
        vault.mint(1, owner, {"from": owner})

    with reverts(error):
        factory.createEVMScript(
            owner,
            create_calldata(
                market_params,
                IRM_CONFIG,
                controller.address,
                STEWARD,
                PAUSER_COMMITTEE,
                False,
                vault=vault.address,
            ),
        )


@pytest.mark.parametrize(
    "setter,error",
    [
        ("setRejectControllerValidation", "INVALID_CONTROLLER_VALIDATION"),
        ("setRejectWrapperValidation", "INVALID_WRAPPER_VALIDATION"),
    ],
)
def test_create_evm_script_uses_market_factory_validation(
    owner,
    factory,
    market_factory_stub,
    controller,
    market_params,
    vault_stub,
    setter,
    error,
):
    getattr(market_factory_stub, setter)(True, {"from": owner})
    with reverts(error):
        factory.createEVMScript(
            owner,
            create_calldata(
                market_params,
                IRM_CONFIG,
                controller.address,
                STEWARD,
                PAUSER_COMMITTEE,
                False,
                vault=vault_stub.address,
            ),
        )
    getattr(market_factory_stub, setter)(False, {"from": owner})


@pytest.mark.parametrize("enable_settlement", [False, True])
@pytest.mark.parametrize("fee", [0, INITIAL_FEE, MAX_FEE])
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
    preseeder,
    vault_stub,
    enable_settlement,
    fee,
):
    "Must append setFee last exactly when the requested initial fee is nonzero"
    calldata = create_calldata(
        market_params,
        IRM_CONFIG,
        controller.address,
        STEWARD,
        PAUSER_COMMITTEE,
        enable_settlement,
        fee,
        vault=vault_stub.address,
    )
    evm_script = factory.createEVMScript(owner, calldata)

    expected_calls = [
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
    expected_calls.append(
        (
            preseeder.address,
            preseeder.preseedMarket.encode_input(market_params, vault_stub.address),
        )
    )
    if fee != 0:
        expected_calls.append((owner_stub.address, owner_stub.setFee.encode_input(market_params, fee)))
    expected_evm_script = encode_call_script(expected_calls)
    assert evm_script == expected_evm_script


@pytest.mark.parametrize("fee", [0, INITIAL_FEE])
def test_activation_permission_accepts_both_fee_script_shapes(
    owner,
    owner_stub,
    irm_router_stub,
    adaptive_curve_irm_stub,
    circuit_breaker_stub,
    risk_steward_dashboard_stub,
    controller,
    market_params,
    factory,
    preseeder,
    EVMScriptPermissionsWrapper,
    vault_stub,
    fee,
):
    permission = (
        adaptive_curve_irm_stub.address
        + adaptive_curve_irm_stub.applyIrmConfig.signature[2:]
        + irm_router_stub.address[2:]
        + irm_router_stub.setMarketIrm.signature[2:]
        + owner_stub.address[2:]
        + owner_stub.createMarket.signature[2:]
        + risk_steward_dashboard_stub.address[2:]
        + risk_steward_dashboard_stub.addMarketSteward.signature[2:]
        + circuit_breaker_stub.address[2:]
        + circuit_breaker_stub.registerPauser.signature[2:]
        + preseeder.address[2:]
        + preseeder.preseedMarket.signature[2:]
        + owner_stub.address[2:]
        + owner_stub.setFee.signature[2:]
    )
    evm_script = factory.createEVMScript(
        owner,
        create_calldata(
            market_params,
            IRM_CONFIG,
            controller.address,
            STEWARD,
            PAUSER_COMMITTEE,
            False,
            fee,
            vault=vault_stub.address,
        ),
    )
    permissions = EVMScriptPermissionsWrapper.deploy({"from": owner})

    assert permissions.canExecuteEVMScript(permission, evm_script)


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_PARAMS, IRM_CONFIG, CONTROLLER, STEWARD, PAUSER_COMMITTEE, True)
    decoded = factory.decodeEVMScriptCallData(calldata)
    (
        market_params,
        irm_config,
        controller,
        enable_settlement,
        steward,
        pauser,
        preseed_vault,
        fee,
    ) = decoded
    assert market_params == MARKET_PARAMS
    assert irm_config == IRM_CONFIG
    assert controller == CONTROLLER
    assert steward == STEWARD
    assert pauser == PAUSER_COMMITTEE
    assert enable_settlement is True
    assert fee == INITIAL_FEE
    assert preseed_vault == VAULT


def test_decode_evm_script_call_data_abi_names():
    decode_abi = next(item for item in LidoLendActivateMarket.abi if item.get("name") == "decodeEVMScriptCallData")
    activation_params = decode_abi["outputs"][0]["components"]

    assert [component["name"] for component in activation_params] == [
        "marketParams",
        "irmConfig",
        "controller",
        "enableSettlement",
        "steward",
        "pauserCommittee",
        "preseedVault",
        "fee",
    ]
