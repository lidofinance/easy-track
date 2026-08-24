from types import SimpleNamespace

import pytest
from brownie import web3

import scripts.deploy_lido_lend_factories as deploy_script
from scripts.deploy_lido_lend_factories import _permissions_plan, _validate_protocol_bindings


def _method(signature):
    return SimpleNamespace(signature=signature)


def test_activation_permission_includes_optional_set_fee_in_execution_order(monkeypatch):
    addresses = {
        "adaptive_curve_irm": "0x" + "11" * 20,
        "irm_router": "0x" + "22" * 20,
        "owner": "0x" + "33" * 20,
        "risk_steward_dashboard": "0x" + "44" * 20,
        "circuit_breaker": "0x" + "55" * 20,
    }
    adaptive_curve_irm = SimpleNamespace(
        address=addresses["adaptive_curve_irm"],
        applyIrmConfig=_method("0x11111111"),
    )
    irm_router = SimpleNamespace(
        address=addresses["irm_router"],
        setMarketIrm=_method("0x22222222"),
    )
    owner = SimpleNamespace(
        address=addresses["owner"],
        setFee=_method("0x44444444"),
    )
    dashboard = SimpleNamespace(
        address=addresses["risk_steward_dashboard"],
        addMarketSteward=_method("0x55555555"),
    )
    circuit_breaker = SimpleNamespace(
        address=addresses["circuit_breaker"],
        registerPauser=_method("0x66666666"),
    )
    monkeypatch.setattr(
        deploy_script,
        "interface",
        SimpleNamespace(
            AdaptiveCurveIrm=lambda _: adaptive_curve_irm,
            IrmRouter=lambda _: irm_router,
            LidoLendOwner=lambda _: owner,
            RiskStewardDashboard=lambda _: dashboard,
            CircuitBreaker=lambda _: circuit_breaker,
        ),
    )

    create_selector = (
        "0x" + web3.keccak(text="createMarket((address,address,address,address,uint256),address,bool)").hex()[2:10]
    )
    permissions = _permissions_plan(addresses, ("LidoLendActivateMarket",))

    assert permissions["LidoLendActivateMarket"] == (
        addresses["adaptive_curve_irm"]
        + "11111111"
        + addresses["irm_router"][2:]
        + "22222222"
        + addresses["owner"][2:]
        + create_selector[2:]
        + addresses["risk_steward_dashboard"][2:]
        + "55555555"
        + addresses["circuit_breaker"][2:]
        + "66666666"
        + addresses["owner"][2:]
        + "44444444"
    )


def test_activation_preflight_requires_executor_fee_manager_role(monkeypatch):
    executor = "0x" + "aa" * 20
    addresses = {
        "core": "0x" + "10" * 20,
        "owner": "0x" + "20" * 20,
        "irm_router": "0x" + "30" * 20,
        "adaptive_curve_irm": "0x" + "40" * 20,
        "risk_steward_dashboard": "0x" + "50" * 20,
        "circuit_breaker": "0x" + "60" * 20,
    }
    fee_manager_role = web3.keccak(text="FEE_MANAGER_ROLE")
    owner = SimpleNamespace(
        LIDO_LEND=lambda: addresses["core"],
        hasRole=lambda role, account: account == executor and role != fee_manager_role,
    )
    monkeypatch.setattr(
        deploy_script,
        "interface",
        SimpleNamespace(
            CircuitBreaker=lambda _: SimpleNamespace(ADMIN=lambda: executor),
            LidoLend=lambda _: SimpleNamespace(owner=lambda: addresses["owner"]),
            LidoLendOwner=lambda _: owner,
            IrmRouter=lambda _: SimpleNamespace(MORPHO=lambda: addresses["core"], manager=lambda: executor),
            AdaptiveCurveIrm=lambda _: SimpleNamespace(
                ROUTER=lambda: addresses["irm_router"], manager=lambda: executor
            ),
            RiskStewardDashboard=lambda _: SimpleNamespace(
                LIDO_LEND=lambda: addresses["core"], hasRole=lambda _role, account: account == executor
            ),
        ),
    )

    with pytest.raises(ValueError, match="executor lacks owner.FEE_MANAGER_ROLE"):
        _validate_protocol_bindings(addresses, executor, ("LidoLendActivateMarket",))
