import pytest

from scripts.deploy_lido_lend_factories import (
    ALL_FACTORY_NAMES,
    _deployment_plan,
    _parse_factory_selection,
    _permissions_plan,
    _required_address_keys,
    _validate_protocol_bindings,
    deploy_lido_lend_factories,
)


FACADE_FACTORIES = {
    "LidoLendAddGuardian",
    "LidoLendRemoveGuardian",
    "LidoLendReplaceGuardian",
    "LidoLendGrantInstantActivation",
    "LidoLendSetGuardiansQuorum",
    "LidoLendSetSuspectWindow",
    "LidoLendUnbanGuardianSignals",
    "LidoLendSetCollateralActivationConfig",
    "LidoLendSetSettlementConfig",
    "LidoLendSetSupplyCap",
    "LidoLendUnfreezeMarket",
}


def test_factory_selection_defaults_to_every_factory():
    assert _parse_factory_selection(None) == ALL_FACTORY_NAMES


def test_factory_selection_accepts_short_and_full_names_in_canonical_order():
    assert _parse_factory_selection("SetSupplyCap, LidoLendAddGuardian") == (
        "LidoLendAddGuardian",
        "LidoLendSetSupplyCap",
    )


@pytest.mark.parametrize(
    "value, error",
    [
        ("", "must not be empty"),
        ("SetSupplyCap,", "empty factory name"),
        ("SetSupplyCap,SetSupplyCap", "Duplicate"),
        ("DoesNotExist", "Unknown"),
    ],
)
def test_factory_selection_rejects_invalid_values(value, error):
    with pytest.raises(ValueError, match=error):
        _parse_factory_selection(value)


def test_selected_factory_only_requires_its_protocol_dependencies():
    assert _required_address_keys(("LidoLendSetSupplyCap",)) == {
        "trusted_caller",
        "core",
        "owner",
        "circuit_breaker",
    }
    assert _required_address_keys(("LidoLendSetMarketExitBookAllowed",)) == {
        "trusted_caller",
        "core",
        "circuit_breaker",
        "morpho_exit_book",
        "erc4626_exit_book",
    }


def test_deploy_selected_lido_lend_factory(lido_lend, easy_track, deployer, trusted_caller):
    """A partial deployment does not need or emit artifacts for unrelated dependencies."""
    selected = _parse_factory_selection("SetSupplyCap")
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": str(lido_lend.contracts["owner"]),
        "circuit_breaker": str(lido_lend.contracts["circuitBreaker"]),
    }

    if lido_lend.easy_track:
        assert _validate_protocol_bindings(addresses, selected) == easy_track.evmScriptExecutor()

    expected_args = {Factory._name: args for Factory, args in _deployment_plan(addresses, selected)}
    expected_permissions = _permissions_plan(addresses, selected)
    artifacts, deployed = deploy_lido_lend_factories(
        addresses,
        {"from": deployer},
        selected,
    )

    assert set(artifacts) == {"LidoLendSetSupplyCap"}
    assert set(expected_permissions) == set(artifacts)
    assert len(deployed) == 1
    Factory, instance = deployed[0]
    assert Factory._name == "LidoLendSetSupplyCap"
    assert artifacts[Factory._name] == {
        "contract": Factory._name,
        "address": instance.address,
        "constructorArgs": expected_args[Factory._name],
        "permissions": expected_permissions[Factory._name],
    }


def test_deploy_lido_lend_factories_scenario(lido_lend, easy_track, deployer, trusted_caller):
    """The deployment helper deploys every factory with the expected immutable protocol bindings."""
    if not lido_lend.has("morphoExitBook") or not lido_lend.has("erc4626ExitBook"):
        # The deployment script intentionally deploys the complete current factory set.
        # Its exit-book factory therefore requires both optional protocol components.
        pytest.skip("deployment has no exit books")

    def address(name):
        return str(lido_lend.contracts[name])

    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": address("core"),
        "owner": address("owner"),
        "irm_router": address("irmRouter"),
        "adaptive_curve_irm": address("adaptiveCurveIrm"),
        "circuit_breaker": address("circuitBreaker"),
        "risk_steward_dashboard": address("riskStewardDashboard"),
        "morpho_exit_book": address("morphoExitBook"),
        "erc4626_exit_book": address("erc4626ExitBook"),
    }
    if lido_lend.easy_track:
        assert _validate_protocol_bindings(addresses) == easy_track.evmScriptExecutor()

    expected_args = {Factory._name: args for Factory, args in _deployment_plan(addresses)}
    expected_permissions = _permissions_plan(addresses)
    artifacts, deployed = deploy_lido_lend_factories(addresses, {"from": deployer})
    instances = {Factory._name: instance for Factory, instance in deployed}

    assert len(instances) == 17
    assert set(artifacts) == set(instances)
    for name, instance in instances.items():
        assert instance.trustedCaller() == trusted_caller
        assert artifacts[name] == {
            "contract": name,
            "address": instance.address,
            "constructorArgs": expected_args[name],
            "permissions": expected_permissions[name],
        }

    permission_entries = {
        name: [blob[i : i + 48] for i in range(2, len(blob), 48)] for name, blob in expected_permissions.items()
    }
    assert all(entries for entries in permission_entries.values())
    assert len(permission_entries["LidoLendActivateMarket"]) == 4
    assert len(permission_entries["LidoLendReplaceGuardian"]) == 2
    assert len(permission_entries["LidoLendSetMarketExitBookAllowed"]) == 2
    assert all(
        len(entries) == 1
        for name, entries in permission_entries.items()
        if name
        not in {
            "LidoLendActivateMarket",
            "LidoLendReplaceGuardian",
            "LidoLendSetMarketExitBookAllowed",
        }
    )
    permission_targets = {
        name: ["0x" + entry[:40].lower() for entry in entries] for name, entries in permission_entries.items()
    }
    assert permission_targets == {
        "LidoLendActivateMarket": [
            addresses["adaptive_curve_irm"].lower(),
            addresses["irm_router"].lower(),
            addresses["owner"].lower(),
            addresses["circuit_breaker"].lower(),
        ],
        "LidoLendAddGuardian": [addresses["owner"].lower()],
        "LidoLendRemoveGuardian": [addresses["owner"].lower()],
        "LidoLendReplaceGuardian": [addresses["owner"].lower(), addresses["owner"].lower()],
        "LidoLendGrantInstantActivation": [addresses["owner"].lower()],
        "LidoLendSetGuardiansQuorum": [addresses["owner"].lower()],
        "LidoLendSetSuspectWindow": [addresses["owner"].lower()],
        "LidoLendUnbanGuardianSignals": [addresses["owner"].lower()],
        "LidoLendSetCollateralActivationConfig": [addresses["owner"].lower()],
        "LidoLendSetSettlementConfig": [addresses["owner"].lower()],
        "LidoLendSetSupplyCap": [addresses["owner"].lower()],
        "LidoLendUnfreezeMarket": [addresses["owner"].lower()],
        "LidoLendSetIrmCurveParams": [addresses["adaptive_curve_irm"].lower()],
        "LidoLendSetMarketIrm": [addresses["irm_router"].lower()],
        "LidoLendAddRiskSteward": [addresses["risk_steward_dashboard"].lower()],
        "LidoLendRemoveRiskSteward": [addresses["risk_steward_dashboard"].lower()],
        "LidoLendSetMarketExitBookAllowed": [
            addresses["morpho_exit_book"].lower(),
            addresses["erc4626_exit_book"].lower(),
        ],
    }

    owner = lido_lend.contract("owner")
    core = lido_lend.contract("core")

    activation = instances["LidoLendActivateMarket"]
    assert activation.lidoLendOwner() == owner
    assert activation.irmRouter() == addresses["irm_router"]
    assert activation.adaptiveCurveIrm() == addresses["adaptive_curve_irm"]
    assert activation.circuitBreaker() == addresses["circuit_breaker"]

    for name in FACADE_FACTORIES:
        assert instances[name].lidoLendOwner() == owner
        assert instances[name].lidoLend() == core

    irm_curve = instances["LidoLendSetIrmCurveParams"]
    assert irm_curve.lidoLend() == core
    assert irm_curve.irmRouter() == addresses["irm_router"]
    assert irm_curve.adaptiveCurveIrm() == addresses["adaptive_curve_irm"]

    market_irm = instances["LidoLendSetMarketIrm"]
    assert market_irm.lidoLend() == core
    assert market_irm.irmRouter() == addresses["irm_router"]

    for name in ("LidoLendAddRiskSteward", "LidoLendRemoveRiskSteward"):
        assert instances[name].lidoLend() == core
        assert instances[name].riskStewardDashboard() == addresses["risk_steward_dashboard"]

    exit_books = instances["LidoLendSetMarketExitBookAllowed"]
    assert exit_books.morphoExitBook() == addresses["morpho_exit_book"]
    assert exit_books.erc4626ExitBook() == addresses["erc4626_exit_book"]
