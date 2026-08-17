import pytest

from scripts.deploy_lido_lend_factories import (
    ALL_FACTORY_NAMES,
    _deployment_plan,
    _parse_factory_selection,
    _permissions_plan,
    _read_addresses,
    _required_address_keys,
    _validate_protocol_bindings,
    deploy_lido_lend_factories,
)


FACADE_FACTORIES = {
    "LidoLendAddGuardian",
    "LidoLendRemoveGuardian",
    "LidoLendReplaceGuardian",
    "LidoLendSetInstantActivation",
    "LidoLendSetGuardiansQuorum",
    "LidoLendSetSuspectWindow",
    "LidoLendUnbanAccount",
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
    assert _parse_factory_selection("UnbanAccount") == ("LidoLendUnbanAccount",)


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
    assert _required_address_keys(("LidoLendActivateMarket",)) == {
        "trusted_caller",
        "core",
        "owner",
        "irm_router",
        "adaptive_curve_irm",
        "risk_steward_dashboard",
        "circuit_breaker",
    }
    assert _required_address_keys(("LidoLendSetSupplyCap",)) == {
        "trusted_caller",
        "core",
        "owner",
    }
    assert _required_address_keys(("LidoLendSetMorphoExitBookAllowed",)) == {
        "trusted_caller",
        "core",
        "morpho_exit_book",
    }
    assert _required_address_keys(("LidoLendSetErc4626ExitBookAllowed",)) == {
        "trusted_caller",
        "core",
        "erc4626_exit_book",
    }


def test_deploy_script_reads_immutable_artifacts(lido_lend, trusted_caller, monkeypatch):
    if lido_lend.local:
        pytest.skip("immutable artifact ingestion is exercised in artifact mode")

    monkeypatch.setenv("TRUSTED_CALLER", trusted_caller.address)
    addresses = _read_addresses(ALL_FACTORY_NAMES)

    def address(name):
        return str(lido_lend.contracts[name])

    assert addresses == {
        "trusted_caller": trusted_caller.address,
        "core": address("core"),
        "owner": address("owner"),
        "irm_router": address("irmRouter"),
        "adaptive_curve_irm": address("adaptiveCurveIrm"),
        "circuit_breaker": address("circuitBreaker"),
        "risk_steward_dashboard": address("riskStewardDashboard"),
        "morpho_exit_book": address("morphoExitBook"),
        "erc4626_exit_book": address("erc4626ExitBook"),
        "evm_script_executor": str(lido_lend.evm_script_executor),
    }


def test_deploy_selected_lido_lend_factory(lido_lend, easy_track, deployer, trusted_caller):
    """A partial deployment does not need or emit artifacts for unrelated dependencies."""
    selected = _parse_factory_selection("SetSupplyCap")
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": str(lido_lend.contracts["owner"]),
    }

    assert (
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), selected)
        == easy_track.evmScriptExecutor()
    )

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
    assert _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor()) == easy_track.evmScriptExecutor()

    expected_args = {Factory._name: args for Factory, args in _deployment_plan(addresses)}
    expected_permissions = _permissions_plan(addresses)
    artifacts, deployed = deploy_lido_lend_factories(addresses, {"from": deployer})
    instances = {Factory._name: instance for Factory, instance in deployed}

    assert len(instances) == 18
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
    assert len(permission_entries["LidoLendActivateMarket"]) == 5
    assert len(permission_entries["LidoLendAddGuardian"]) == 2
    assert len(permission_entries["LidoLendRemoveGuardian"]) == 2
    assert all(
        len(entries) == 1
        for name, entries in permission_entries.items()
        if name not in {"LidoLendActivateMarket", "LidoLendAddGuardian", "LidoLendRemoveGuardian"}
    )
    permission_targets = {
        name: ["0x" + entry[:40].lower() for entry in entries] for name, entries in permission_entries.items()
    }
    assert permission_targets == {
        "LidoLendActivateMarket": [
            addresses["adaptive_curve_irm"].lower(),
            addresses["irm_router"].lower(),
            addresses["owner"].lower(),
            addresses["risk_steward_dashboard"].lower(),
            addresses["circuit_breaker"].lower(),
        ],
        "LidoLendAddGuardian": [addresses["owner"].lower(), addresses["owner"].lower()],
        "LidoLendRemoveGuardian": [addresses["owner"].lower(), addresses["owner"].lower()],
        "LidoLendReplaceGuardian": [addresses["owner"].lower()],
        "LidoLendSetInstantActivation": [addresses["owner"].lower()],
        "LidoLendSetGuardiansQuorum": [addresses["owner"].lower()],
        "LidoLendSetSuspectWindow": [addresses["owner"].lower()],
        "LidoLendUnbanAccount": [addresses["owner"].lower()],
        "LidoLendSetCollateralActivationConfig": [addresses["owner"].lower()],
        "LidoLendSetSettlementConfig": [addresses["owner"].lower()],
        "LidoLendSetSupplyCap": [addresses["owner"].lower()],
        "LidoLendUnfreezeMarket": [addresses["owner"].lower()],
        "LidoLendSetIrmConfig": [addresses["adaptive_curve_irm"].lower()],
        "LidoLendSetMarketIrm": [addresses["irm_router"].lower()],
        "LidoLendAddRiskSteward": [addresses["risk_steward_dashboard"].lower()],
        "LidoLendRemoveRiskSteward": [addresses["risk_steward_dashboard"].lower()],
        "LidoLendSetMorphoExitBookAllowed": [addresses["morpho_exit_book"].lower()],
        "LidoLendSetErc4626ExitBookAllowed": [addresses["erc4626_exit_book"].lower()],
    }

    owner = lido_lend.contract("owner")
    core = lido_lend.contract("core")

    activation = instances["LidoLendActivateMarket"]
    assert activation.lidoLendOwner() == owner
    assert activation.irmRouter() == addresses["irm_router"]
    assert activation.adaptiveCurveIrm() == addresses["adaptive_curve_irm"]
    assert activation.circuitBreaker() == addresses["circuit_breaker"]
    assert activation.riskStewardDashboard() == addresses["risk_steward_dashboard"]

    for name in FACADE_FACTORIES:
        assert instances[name].lidoLendOwner() == owner

    irm_config = instances["LidoLendSetIrmConfig"]
    assert irm_config.lidoLend() == core
    assert irm_config.irmRouter() == addresses["irm_router"]
    assert irm_config.adaptiveCurveIrm() == addresses["adaptive_curve_irm"]

    market_irm = instances["LidoLendSetMarketIrm"]
    assert market_irm.lidoLend() == core
    assert market_irm.irmRouter() == addresses["irm_router"]

    for name in ("LidoLendAddRiskSteward", "LidoLendRemoveRiskSteward"):
        assert instances[name].riskStewardDashboard() == addresses["risk_steward_dashboard"]

    assert instances["LidoLendSetMorphoExitBookAllowed"].morphoExitBook() == addresses["morpho_exit_book"]
    assert instances["LidoLendSetErc4626ExitBookAllowed"].erc4626ExitBook() == addresses["erc4626_exit_book"]


def test_preflight_rejects_executor_other_than_easy_track(lido_lend, easy_track, trusted_caller, stranger):
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": str(lido_lend.contracts["owner"]),
        "evm_script_executor": stranger.address,
    }
    with pytest.raises(ValueError, match="protocol artifact executor does not match"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendSetSupplyCap",))


def test_preflight_rejects_wrong_core(lido_lend, easy_track, deployer, trusted_caller, LidoLendCoreStub):
    wrong_core = LidoLendCoreStub.deploy({"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": wrong_core.address,
        "owner": str(lido_lend.contracts["owner"]),
    }
    with pytest.raises(ValueError, match="owner.LIDO_LEND mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendSetSupplyCap",))


def test_preflight_rejects_owner_bound_to_another_core(
    lido_lend, easy_track, deployer, trusted_caller, LidoLendCoreStub, LidoLendOwnerStub
):
    wrong_core = LidoLendCoreStub.deploy({"from": deployer})
    wrong_owner = LidoLendOwnerStub.deploy({"from": deployer})
    wrong_owner.setCore(wrong_core, {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": wrong_owner.address,
    }
    with pytest.raises(ValueError, match="owner.LIDO_LEND mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendSetSupplyCap",))


def test_preflight_rejects_owner_without_executor_role(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    LidoLendCoreStub,
    LidoLendOwnerStub,
):
    core = LidoLendCoreStub.deploy({"from": deployer})
    wrong_owner = LidoLendOwnerStub.deploy({"from": deployer})
    wrong_owner.setCore(core, {"from": deployer})
    core.setOwner(wrong_owner, {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": core.address,
        "owner": wrong_owner.address,
    }
    with pytest.raises(ValueError, match="executor lacks owner.MARKET_MANAGER_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendSetSupplyCap",))


def test_preflight_rejects_facade_that_does_not_own_core(
    lido_lend, easy_track, deployer, trusted_caller, LidoLendOwnerStub
):
    facade = LidoLendOwnerStub.deploy({"from": deployer})
    facade.setCore(lido_lend.contracts["core"], {"from": deployer})
    facade.grantRole(facade.MARKET_MANAGER_ROLE(), easy_track.evmScriptExecutor(), {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": facade.address,
    }
    with pytest.raises(ValueError, match="core.owner mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendSetSupplyCap",))


def test_preflight_rejects_router_bound_to_wrong_core(lido_lend, easy_track, deployer, trusted_caller, IrmRouterStub):
    wrong_router = IrmRouterStub.deploy({"from": deployer})
    wrong_router.setMorpho(trusted_caller, {"from": deployer})
    wrong_router.setManager(easy_track.evmScriptExecutor(), {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "irm_router": wrong_router.address,
    }
    with pytest.raises(ValueError, match="irm_router.MORPHO mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendSetMarketIrm",))


def test_preflight_rejects_circuit_breaker_with_wrong_admin(
    lido_lend, easy_track, deployer, trusted_caller, stranger, CircuitBreakerStub
):
    wrong_circuit_breaker = CircuitBreakerStub.deploy(stranger, {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": str(lido_lend.contracts["owner"]),
        "irm_router": str(lido_lend.contracts["irmRouter"]),
        "adaptive_curve_irm": str(lido_lend.contracts["adaptiveCurveIrm"]),
        "circuit_breaker": wrong_circuit_breaker.address,
        "risk_steward_dashboard": str(lido_lend.contracts["riskStewardDashboard"]),
    }
    with pytest.raises(ValueError, match="does not match EasyTrack evmScriptExecutor"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendActivateMarket",))


def test_preflight_rejects_activation_without_dashboard_executor_role(
    lido_lend, easy_track, deployer, trusted_caller, RiskStewardDashboardStub
):
    dashboard = RiskStewardDashboardStub.deploy({"from": deployer})
    dashboard.setLidoLend(lido_lend.contracts["core"], {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": str(lido_lend.contracts["owner"]),
        "irm_router": str(lido_lend.contracts["irmRouter"]),
        "adaptive_curve_irm": str(lido_lend.contracts["adaptiveCurveIrm"]),
        "circuit_breaker": str(lido_lend.contracts["circuitBreaker"]),
        "risk_steward_dashboard": dashboard.address,
    }
    with pytest.raises(ValueError, match="executor lacks risk_steward_dashboard.STEWARD_ADMIN_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendActivateMarket",))
