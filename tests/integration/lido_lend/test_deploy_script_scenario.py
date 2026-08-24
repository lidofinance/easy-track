from types import SimpleNamespace

import pytest

import scripts.deploy_lido_lend_factories as deploy_script

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
    "LidoLendSetFee",
    "LidoLendSetFeeRecipient",
    "LidoLendUnfreezeMarket",
}


def test_factory_selection_defaults_to_every_factory():
    assert _parse_factory_selection(None) == ALL_FACTORY_NAMES


def test_default_factory_selection_includes_fee_management():
    assert "LidoLendSetFee" in ALL_FACTORY_NAMES
    assert "LidoLendSetFeeRecipient" in ALL_FACTORY_NAMES
    assert "LidoLendSetExitBooksServiceFee" in ALL_FACTORY_NAMES


def test_fee_recipient_permissions_accrue_on_core_before_calling_facade(monkeypatch):
    core_address = "0x" + "11" * 20
    owner_address = "0x" + "22" * 20
    accrue_selector = "0x12345678"
    set_recipient_selector = "0x90abcdef"
    core = SimpleNamespace(
        address=core_address,
        accrueInterest=SimpleNamespace(signature=accrue_selector),
    )
    owner = SimpleNamespace(
        address=owner_address,
        setFeeRecipient=SimpleNamespace(signature=set_recipient_selector),
    )
    monkeypatch.setattr(
        deploy_script,
        "interface",
        SimpleNamespace(LidoLend=lambda _: core, LidoLendOwner=lambda _: owner),
    )

    permissions = _permissions_plan(
        {"core": core_address, "owner": owner_address},
        ("LidoLendSetFeeRecipient",),
    )

    assert permissions["LidoLendSetFeeRecipient"] == (
        core_address + accrue_selector[2:] + owner_address[2:] + set_recipient_selector[2:]
    )


def test_exit_book_deployment_uses_dynamic_targets_and_artifact_permissions(monkeypatch):
    morpho_address = "0x" + "33" * 20
    erc4626_address = "0x" + "44" * 20
    set_fee_selector = "0x12345678"
    set_market_allowed_selector = "0x23456789"
    set_vault_allowed_selector = "0x34567890"
    morpho = SimpleNamespace(
        address=morpho_address,
        setServiceFee=SimpleNamespace(signature=set_fee_selector),
        setMarketAllowed=SimpleNamespace(signature=set_market_allowed_selector),
    )
    erc4626 = SimpleNamespace(
        address=erc4626_address,
        setServiceFee=SimpleNamespace(signature=set_fee_selector),
        setVaultAllowed=SimpleNamespace(signature=set_vault_allowed_selector),
    )
    monkeypatch.setattr(
        deploy_script,
        "interface",
        SimpleNamespace(
            MorphoExitBook=lambda _: morpho,
            Erc4626ExitBook=lambda _: erc4626,
        ),
    )
    addresses = {
        "trusted_caller": "0x" + "11" * 20,
        "core": "0x" + "22" * 20,
        "morpho_exit_book": morpho_address,
        "erc4626_exit_book": erc4626_address,
    }

    selected = (
        "LidoLendSetMorphoExitBookAllowed",
        "LidoLendSetErc4626ExitBookAllowed",
        "LidoLendSetExitBooksServiceFee",
    )
    plan = _deployment_plan(addresses, selected)
    permissions = _permissions_plan(addresses, selected)

    assert [(Factory._name, args) for Factory, args in plan] == [
        (name, [addresses["trusted_caller"]]) for name in selected
    ]
    assert permissions["LidoLendSetMorphoExitBookAllowed"] == (morpho_address + set_market_allowed_selector[2:])
    assert permissions["LidoLendSetErc4626ExitBookAllowed"] == (erc4626_address + set_vault_allowed_selector[2:])
    assert permissions["LidoLendSetExitBooksServiceFee"] == (
        morpho_address + set_fee_selector[2:] + erc4626_address[2:] + set_fee_selector[2:]
    )


def test_factory_selection_accepts_short_and_full_names_in_canonical_order():
    assert _parse_factory_selection("SetSupplyCap, LidoLendAddGuardian") == (
        "LidoLendAddGuardian",
        "LidoLendSetSupplyCap",
    )
    assert _parse_factory_selection("UnbanAccount") == ("LidoLendUnbanAccount",)
    assert _parse_factory_selection("RegisterPauser") == ("LidoLendRegisterPauser",)


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
    assert _required_address_keys(("LidoLendRegisterPauser",)) == {
        "trusted_caller",
        "core",
        "circuit_breaker",
    }
    assert _required_address_keys(("LidoLendSetSupplyCap",)) == {
        "trusted_caller",
        "core",
        "owner",
    }
    assert _required_address_keys(("LidoLendSetFeeRecipient",)) == {
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
    assert _required_address_keys(("LidoLendSetExitBooksServiceFee",)) == {
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

    assert len(instances) == 22
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
    assert len(permission_entries["LidoLendActivateMarket"]) == 6
    assert len(permission_entries["LidoLendAddGuardian"]) == 2
    assert len(permission_entries["LidoLendRemoveGuardian"]) == 2
    assert len(permission_entries["LidoLendSetFeeRecipient"]) == 2
    assert len(permission_entries["LidoLendSetExitBooksServiceFee"]) == 2
    assert all(
        len(entries) == 1
        for name, entries in permission_entries.items()
        if name
        not in {
            "LidoLendActivateMarket",
            "LidoLendAddGuardian",
            "LidoLendRemoveGuardian",
            "LidoLendSetFeeRecipient",
            "LidoLendSetExitBooksServiceFee",
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
            addresses["risk_steward_dashboard"].lower(),
            addresses["circuit_breaker"].lower(),
            addresses["owner"].lower(),
        ],
        "LidoLendRegisterPauser": [addresses["circuit_breaker"].lower()],
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
        "LidoLendSetFee": [addresses["owner"].lower()],
        "LidoLendSetFeeRecipient": [addresses["core"].lower(), addresses["owner"].lower()],
        "LidoLendUnfreezeMarket": [addresses["owner"].lower()],
        "LidoLendSetIrmConfig": [addresses["adaptive_curve_irm"].lower()],
        "LidoLendSetMarketIrm": [addresses["irm_router"].lower()],
        "LidoLendAddRiskSteward": [addresses["risk_steward_dashboard"].lower()],
        "LidoLendRemoveRiskSteward": [addresses["risk_steward_dashboard"].lower()],
        "LidoLendSetMorphoExitBookAllowed": [addresses["morpho_exit_book"].lower()],
        "LidoLendSetErc4626ExitBookAllowed": [addresses["erc4626_exit_book"].lower()],
        "LidoLendSetExitBooksServiceFee": [
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
    assert activation.riskStewardDashboard() == addresses["risk_steward_dashboard"]

    register_pauser = instances["LidoLendRegisterPauser"]
    assert register_pauser.lidoLend() == core
    assert register_pauser.circuitBreaker() == addresses["circuit_breaker"]

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


def test_preflight_rejects_exit_book_without_executor_fee_role(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    MorphoExitBookStub,
    Erc4626ExitBookStub,
):
    morpho = MorphoExitBookStub.deploy({"from": deployer})
    morpho.setMorpho(lido_lend.contracts["core"], {"from": deployer})
    erc4626 = Erc4626ExitBookStub.deploy({"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": str(lido_lend.contracts["core"]),
        "morpho_exit_book": morpho.address,
        "erc4626_exit_book": erc4626.address,
    }

    with pytest.raises(ValueError, match="executor lacks morpho_exit_book.FEE_MANAGER_ROLE"):
        _validate_protocol_bindings(
            addresses,
            easy_track.evmScriptExecutor(),
            ("LidoLendSetExitBooksServiceFee",),
        )


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


def test_preflight_rejects_owner_without_executor_fee_role(
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
    with pytest.raises(ValueError, match="executor lacks owner.FEE_MANAGER_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendSetFee",))


def test_preflight_rejects_activation_without_executor_fee_role(
    lido_lend,
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
    owner.grantRole(owner.MARKET_CREATOR_ROLE(), easy_track.evmScriptExecutor(), {"from": deployer})
    addresses = {
        "trusted_caller": trusted_caller.address,
        "core": core.address,
        "owner": owner.address,
        "irm_router": str(lido_lend.contracts["irmRouter"]),
        "adaptive_curve_irm": str(lido_lend.contracts["adaptiveCurveIrm"]),
        "circuit_breaker": str(lido_lend.contracts["circuitBreaker"]),
        "risk_steward_dashboard": str(lido_lend.contracts["riskStewardDashboard"]),
    }

    with pytest.raises(ValueError, match="executor lacks owner.FEE_MANAGER_ROLE"):
        _validate_protocol_bindings(addresses, easy_track.evmScriptExecutor(), ("LidoLendActivateMarket",))


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
