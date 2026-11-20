from types import SimpleNamespace

import pytest
from brownie import web3

import scripts.deploy_lido_lend_factories as deploy_script
from scripts.deploy_lido_lend_factories import _validate_protocol_bindings


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


def test_exit_book_preflight_does_not_require_executor_fee_manager_role(monkeypatch):
    executor = "0x" + "aa" * 20
    addresses = {
        "core": "0x" + "10" * 20,
        "morpho_exit_book": "0x" + "20" * 20,
        "erc4626_exit_book": "0x" + "30" * 20,
    }
    morpho = SimpleNamespace(
        MORPHO=lambda: addresses["core"],
        hasRole=lambda _role, account: account == executor,
    )
    erc4626 = SimpleNamespace(hasRole=lambda _role, account: account == executor)
    monkeypatch.setattr(
        deploy_script,
        "interface",
        SimpleNamespace(
            MorphoExitBook=lambda _: morpho,
            Erc4626ExitBook=lambda _: erc4626,
        ),
    )

    assert _validate_protocol_bindings(addresses, executor, ("LidoLendExitBookActions",)) == executor
