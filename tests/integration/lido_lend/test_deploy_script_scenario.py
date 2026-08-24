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
    "LidoLendGuardianActions",
    "LidoLendMarketManagerActions",
}


def _expected_artifact(name, address, constructor_args, permissions):
    return {
        "contract": name,
        "address": address,
        "constructorArgs": constructor_args,
        "permissions": permissions,
    }


def test_factory_selection_defaults_to_every_factory():
    assert _parse_factory_selection(None) == ALL_FACTORY_NAMES


def test_factory_selection_accepts_short_and_full_names_in_canonical_order():
    assert _parse_factory_selection("MarketManagerActions, LidoLendGuardianActions") == (
        "LidoLendGuardianActions",
        "LidoLendMarketManagerActions",
    )
    assert _parse_factory_selection("ExitBookActions") == ("LidoLendExitBookActions",)
    assert _parse_factory_selection("RegisterPauser") == ("LidoLendRegisterPauser",)


@pytest.mark.parametrize(
    "value, error",
    [
        ("", "must not be empty"),
        ("MarketManagerActions,", "empty factory name"),
        ("MarketManagerActions,MarketManagerActions", "Duplicate"),
        ("SetSupplyCap", "Unknown"),
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
    assert _required_address_keys(("LidoLendRegisterPauser",)) == {
        "trusted_caller",
        "core",
        "circuit_breaker",
    }
    assert _required_address_keys(("LidoLendMarketManagerActions",)) == {
        "trusted_caller",
        "core",
        "owner",
    }
    assert _required_address_keys(("LidoLendGuardianActions",)) == {
        "trusted_caller",
        "core",
        "owner",
    }
    assert _required_address_keys(("LidoLendRiskStewardActions",)) == {
        "trusted_caller",
        "core",
        "risk_steward_dashboard",
    }
    assert _required_address_keys(("LidoLendIrmActions",)) == {
        "trusted_caller",
        "core",
        "irm_router",
        "adaptive_curve_irm",
    }
    assert _required_address_keys(("LidoLendExitBookActions",)) == {
        "trusted_caller",
        "core",
        "morpho_exit_book",
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
    selected = _parse_factory_selection("MarketManagerActions")
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

    assert set(artifacts) == {"LidoLendMarketManagerActions"}
    assert set(expected_permissions) == set(artifacts)
    assert len(deployed) == 1
    Factory, instance = deployed[0]
    assert Factory._name == "LidoLendMarketManagerActions"
    assert artifacts[Factory._name] == _expected_artifact(
        Factory._name,
        instance.address,
        expected_args[Factory._name],
        expected_permissions[Factory._name],
    )


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

    assert len(instances) == 7
    assert set(artifacts) == set(instances)
    for name, instance in instances.items():
        assert instance.trustedCaller() == trusted_caller
        assert artifacts[name] == _expected_artifact(
            name,
            instance.address,
            expected_args[name],
            expected_permissions[name],
        )

    permission_entries = {
        name: [blob[i : i + 48].lower() for i in range(2, len(blob), 48)] for name, blob in expected_permissions.items()
    }
    assert all(entries for entries in permission_entries.values())
    assert {name: len(entries) for name, entries in permission_entries.items()} == {
        "LidoLendActivateMarket": 5,
        "LidoLendRegisterPauser": 1,
        "LidoLendGuardianActions": 6,
        "LidoLendMarketManagerActions": 5,
        "LidoLendRiskStewardActions": 2,
        "LidoLendIrmActions": 2,
        "LidoLendExitBookActions": 2,
    }
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
        "LidoLendRegisterPauser": [addresses["circuit_breaker"].lower()],
        "LidoLendGuardianActions": [addresses["owner"].lower()] * 6,
        "LidoLendMarketManagerActions": [addresses["owner"].lower()] * 5,
        "LidoLendRiskStewardActions": [addresses["risk_steward_dashboard"].lower()] * 2,
        "LidoLendIrmActions": [
            addresses["adaptive_curve_irm"].lower(),
            addresses["irm_router"].lower(),
        ],
        "LidoLendExitBookActions": [
            addresses["morpho_exit_book"].lower(),
            addresses["erc4626_exit_book"].lower(),
        ],
    }

    owner = lido_lend.contract("owner")
    core = lido_lend.contract("core")
    dashboard = lido_lend.contract("riskStewardDashboard")
    adaptive_curve_irm = lido_lend.contract("adaptiveCurveIrm")
    irm_router = lido_lend.contract("irmRouter")
    morpho_exit_book = lido_lend.contract("morphoExitBook")
    erc4626_exit_book = lido_lend.contract("erc4626ExitBook")

    def permission_entry(target, method):
        return target.address[2:].lower() + method.signature[2:].lower()

    expected_group_permissions = {
        "LidoLendGuardianActions": [
            permission_entry(owner, owner.addGuardian),
            permission_entry(owner, owner.setGuardiansQuorum),
            permission_entry(owner, owner.removeGuardian),
            permission_entry(owner, owner.replaceGuardian),
            permission_entry(owner, owner.setGuardiansSuspectWindow),
            permission_entry(owner, owner.unbanGuardianSignals),
        ],
        "LidoLendMarketManagerActions": [
            permission_entry(owner, owner.setInstantActivation),
            permission_entry(owner, owner.setMarketCollateralActivationConfig),
            permission_entry(owner, owner.setMarketSettlementConfig),
            permission_entry(owner, owner.setMarketSupplyCap),
            permission_entry(owner, owner.unfreezeMarket),
        ],
        "LidoLendRiskStewardActions": [
            permission_entry(dashboard, dashboard.addMarketSteward),
            permission_entry(dashboard, dashboard.removeMarketSteward),
        ],
        "LidoLendIrmActions": [
            permission_entry(adaptive_curve_irm, adaptive_curve_irm.applyIrmConfig),
            permission_entry(irm_router, irm_router.setMarketIrm),
        ],
        "LidoLendExitBookActions": [
            permission_entry(morpho_exit_book, morpho_exit_book.setMarketAllowed),
            permission_entry(erc4626_exit_book, erc4626_exit_book.setVaultAllowed),
        ],
    }
    assert {name: permission_entries[name] for name in expected_group_permissions} == expected_group_permissions

    activation = instances["LidoLendActivateMarket"]
    assert activation.lidoLendOwner() == owner
    assert activation.irmRouter() == addresses["irm_router"]
    assert activation.adaptiveCurveIrm() == addresses["adaptive_curve_irm"]
    assert activation.circuitBreaker() == addresses["circuit_breaker"]
    assert activation.riskStewardDashboard() == addresses["risk_steward_dashboard"]

    register_pauser = instances["LidoLendRegisterPauser"]
    assert register_pauser.lidoLend() == core
    assert register_pauser.circuitBreaker() == addresses["circuit_breaker"]

    for name in FACADE_FACTORIES:
        assert instances[name].lidoLendOwner() == owner

    irm_actions = instances["LidoLendIrmActions"]
    assert irm_actions.lidoLend() == core
    assert irm_actions.irmRouter() == addresses["irm_router"]
    assert irm_actions.adaptiveCurveIrm() == addresses["adaptive_curve_irm"]

    assert instances["LidoLendRiskStewardActions"].riskStewardDashboard() == addresses["risk_steward_dashboard"]

    exit_book_actions = instances["LidoLendExitBookActions"]
    assert exit_book_actions.morphoExitBook() == addresses["morpho_exit_book"]
    assert exit_book_actions.erc4626ExitBook() == addresses["erc4626_exit_book"]


def test_preflight_rejects_executor_other_than_easy_track(lido_lend, easy_track, trusted_caller, stranger):
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "owner": str(lido_lend.contracts["owner"]),
        "evm_script_executor": stranger.address,
    }
    with pytest.raises(ValueError, match="protocol artifact executor does not match"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendMarketManagerActions",))


def test_preflight_rejects_wrong_core(lido_lend, easy_track, deployer, trusted_caller, LidoLendCoreStub):
    wrong_core = LidoLendCoreStub.deploy({"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": wrong_core.address,
        "owner": str(lido_lend.contracts["owner"]),
    }
    with pytest.raises(ValueError, match="owner.LIDO_LEND mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendMarketManagerActions",))


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
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendMarketManagerActions",))


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
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendMarketManagerActions",))


def test_preflight_rejects_owner_without_guardian_manager_role(
    easy_track,
    deployer,
    trusted_caller,
    LidoLendCoreStub,
    LidoLendOwnerStub,
):
    core = LidoLendCoreStub.deploy({"from": deployer})
    owner = LidoLendOwnerStub.deploy({"from": deployer})
    owner.setCore(core, {"from": deployer})
    core.setOwner(owner, {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": core.address,
        "owner": owner.address,
    }
    with pytest.raises(ValueError, match="executor lacks owner.GUARDIAN_MANAGER_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendGuardianActions",))


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
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendMarketManagerActions",))


def test_preflight_rejects_router_bound_to_wrong_core(lido_lend, easy_track, deployer, trusted_caller, IrmRouterStub):
    wrong_router = IrmRouterStub.deploy({"from": deployer})
    wrong_router.setMorpho(trusted_caller, {"from": deployer})
    wrong_router.setManager(easy_track.evmScriptExecutor(), {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "irm_router": wrong_router.address,
        "adaptive_curve_irm": str(lido_lend.contracts["adaptiveCurveIrm"]),
    }
    with pytest.raises(ValueError, match="irm_router.MORPHO mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendIrmActions",))


def test_preflight_rejects_irm_router_with_wrong_manager(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    stranger,
    IrmRouterStub,
):
    router = IrmRouterStub.deploy({"from": deployer})
    router.setMorpho(lido_lend.contracts["core"], {"from": deployer})
    router.setManager(stranger, {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "irm_router": router.address,
        "adaptive_curve_irm": str(lido_lend.contracts["adaptiveCurveIrm"]),
    }
    with pytest.raises(ValueError, match="irm_router.manager mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendIrmActions",))


def test_preflight_rejects_adaptive_curve_irm_with_wrong_manager(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    stranger,
    AdaptiveCurveIrmStub,
):
    adaptive_curve_irm = AdaptiveCurveIrmStub.deploy({"from": deployer})
    adaptive_curve_irm.setRouter(lido_lend.contracts["irmRouter"], {"from": deployer})
    adaptive_curve_irm.setManager(stranger, {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "irm_router": str(lido_lend.contracts["irmRouter"]),
        "adaptive_curve_irm": adaptive_curve_irm.address,
    }
    with pytest.raises(ValueError, match="adaptive_curve_irm.manager mismatch"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendIrmActions",))


def test_preflight_rejects_risk_dashboard_without_executor_role(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    RiskStewardDashboardStub,
):
    dashboard = RiskStewardDashboardStub.deploy({"from": deployer})
    dashboard.setLidoLend(lido_lend.contracts["core"], {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "risk_steward_dashboard": dashboard.address,
    }
    with pytest.raises(ValueError, match="executor lacks risk_steward_dashboard.STEWARD_ADMIN_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendRiskStewardActions",))


def test_preflight_rejects_exit_books_without_executor_roles(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    MorphoExitBookStub,
    Erc4626ExitBookStub,
):
    morpho_exit_book = MorphoExitBookStub.deploy({"from": deployer})
    morpho_exit_book.setMorpho(lido_lend.contracts["core"], {"from": deployer})
    erc4626_exit_book = Erc4626ExitBookStub.deploy({"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "morpho_exit_book": morpho_exit_book.address,
        "erc4626_exit_book": erc4626_exit_book.address,
    }

    with pytest.raises(ValueError, match="executor lacks morpho_exit_book.ALLOWLIST_MANAGER_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendExitBookActions",))

    morpho_exit_book.grantRole(
        morpho_exit_book.ALLOWLIST_MANAGER_ROLE(),
        easy_track.evmScriptExecutor(),
        {"from": deployer},
    )
    with pytest.raises(ValueError, match="executor lacks erc4626_exit_book.ALLOWLIST_MANAGER_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendExitBookActions",))


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
