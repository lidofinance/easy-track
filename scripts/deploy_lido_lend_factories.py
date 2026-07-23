"""Deploys the Lido Lend EasyTrack factories.

Protocol addresses are read from environment variables because the Lido Lend backbone is deployed
separately from EasyTrack. Set:

  TRUSTED_CALLER                     - committee address allowed to create motions
  LIDO_LEND_CORE                     - LidoLend core (OssifiableProxy hosting all markets)
  LIDO_LEND_OWNER                    - LidoLendOwner facade
  LIDO_LEND_IRM_ROUTER               - IrmRouter
  LIDO_LEND_ADAPTIVE_CURVE_IRM       - AdaptiveCurveIrm singleton
  LIDO_LEND_CIRCUIT_BREAKER          - CircuitBreaker
  LIDO_LEND_RISK_STEWARD_DASHBOARD   - RiskStewardDashboard
  LIDO_LEND_MORPHO_EXIT_BOOK         - MorphoExitBook
  LIDO_LEND_ERC4626_EXIT_BOOK        - Erc4626ExitBook
  LIDO_LEND_FACTORIES                - optional comma-separated factory names; defaults to all

Only addresses used by the selected factories are required (apart from the core and CircuitBreaker used by
the preflight). Before deployment the script verifies that these contracts belong to one Lido Lend deployment
and that the EVMScriptExecutor (`CircuitBreaker.ADMIN`) has the roles required by the selected factories. The
output artifact includes the exact fixed EasyTrack permission blob for each deployed factory.
"""

import json
import os

from brownie import (
    chain,
    interface,
    network,
    web3,
    LidoLendActivateMarket,
    LidoLendAddGuardian,
    LidoLendRemoveGuardian,
    LidoLendReplaceGuardian,
    LidoLendGrantInstantActivation,
    LidoLendSetGuardiansQuorum,
    LidoLendSetSuspectWindow,
    LidoLendUnbanGuardianSignals,
    LidoLendSetCollateralActivationConfig,
    LidoLendSetSettlementConfig,
    LidoLendSetSupplyCap,
    LidoLendUnfreezeMarket,
    LidoLendSetIrmCurveParams,
    LidoLendSetMarketIrm,
    LidoLendAddRiskSteward,
    LidoLendRemoveRiskSteward,
    LidoLendSetMarketExitBookAllowed,
)

from utils import log
from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)


def _env_address(name):
    if name not in os.environ:
        raise EnvironmentError(f"Please set {name} env variable")
    value = os.environ[name]
    assert web3.is_address(value), f"{name} is not a valid address: {value}"
    return value


ALL_FACTORY_NAMES = (
    "LidoLendActivateMarket",
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
    "LidoLendSetIrmCurveParams",
    "LidoLendSetMarketIrm",
    "LidoLendAddRiskSteward",
    "LidoLendRemoveRiskSteward",
    "LidoLendSetMarketExitBookAllowed",
)

MARKET_MANAGER_FACTORIES = {
    "LidoLendGrantInstantActivation",
    "LidoLendSetCollateralActivationConfig",
    "LidoLendSetSettlementConfig",
    "LidoLendSetSupplyCap",
    "LidoLendUnfreezeMarket",
}
GUARDIAN_MANAGER_FACTORIES = {
    "LidoLendAddGuardian",
    "LidoLendRemoveGuardian",
    "LidoLendReplaceGuardian",
    "LidoLendSetGuardiansQuorum",
    "LidoLendSetSuspectWindow",
    "LidoLendUnbanGuardianSignals",
}
OWNER_FACTORIES = (
    {"LidoLendActivateMarket"}
    | MARKET_MANAGER_FACTORIES
    | GUARDIAN_MANAGER_FACTORIES
)
IRM_ROUTER_FACTORIES = {
    "LidoLendActivateMarket",
    "LidoLendSetIrmCurveParams",
    "LidoLendSetMarketIrm",
}
IRM_ROUTER_TARGET_FACTORIES = {
    "LidoLendActivateMarket",
    "LidoLendSetMarketIrm",
}
ADAPTIVE_CURVE_IRM_FACTORIES = {
    "LidoLendActivateMarket",
    "LidoLendSetIrmCurveParams",
}
RISK_STEWARD_FACTORIES = {
    "LidoLendAddRiskSteward",
    "LidoLendRemoveRiskSteward",
}
EXIT_BOOK_FACTORIES = {"LidoLendSetMarketExitBookAllowed"}


def _parse_factory_selection(value):
    """Resolve a comma-separated list of full or `LidoLend`-prefix-free factory names."""
    if value is None:
        return ALL_FACTORY_NAMES
    if not value.strip():
        raise ValueError("LIDO_LEND_FACTORIES must not be empty")

    requested = []
    for raw_name in value.split(","):
        name = raw_name.strip()
        if not name:
            raise ValueError("LIDO_LEND_FACTORIES contains an empty factory name")
        canonical_name = name if name.startswith("LidoLend") else f"LidoLend{name}"
        if canonical_name not in ALL_FACTORY_NAMES:
            valid_names = ", ".join(name.removeprefix("LidoLend") for name in ALL_FACTORY_NAMES)
            raise ValueError(f"Unknown Lido Lend factory: {name}. Valid names: {valid_names}")
        if canonical_name in requested:
            raise ValueError(f"Duplicate Lido Lend factory: {name}")
        requested.append(canonical_name)

    requested_set = set(requested)
    return tuple(name for name in ALL_FACTORY_NAMES if name in requested_set)


def _required_address_keys(factory_names):
    selected = set(factory_names)
    keys = {"trusted_caller", "core", "circuit_breaker"}
    if selected & OWNER_FACTORIES:
        keys.add("owner")
    if selected & IRM_ROUTER_FACTORIES:
        keys.add("irm_router")
    if selected & ADAPTIVE_CURVE_IRM_FACTORIES:
        keys.add("adaptive_curve_irm")
    if selected & RISK_STEWARD_FACTORIES:
        keys.add("risk_steward_dashboard")
    if selected & EXIT_BOOK_FACTORIES:
        keys.update(("morpho_exit_book", "erc4626_exit_book"))
    return keys


ADDRESS_ENV_VARS = {
    "trusted_caller": "TRUSTED_CALLER",
    "core": "LIDO_LEND_CORE",
    "owner": "LIDO_LEND_OWNER",
    "irm_router": "LIDO_LEND_IRM_ROUTER",
    "adaptive_curve_irm": "LIDO_LEND_ADAPTIVE_CURVE_IRM",
    "circuit_breaker": "LIDO_LEND_CIRCUIT_BREAKER",
    "risk_steward_dashboard": "LIDO_LEND_RISK_STEWARD_DASHBOARD",
    "morpho_exit_book": "LIDO_LEND_MORPHO_EXIT_BOOK",
    "erc4626_exit_book": "LIDO_LEND_ERC4626_EXIT_BOOK",
}


def _read_addresses(factory_names):
    required_keys = _required_address_keys(factory_names)
    return {key: _env_address(env_var) for key, env_var in ADDRESS_ENV_VARS.items() if key in required_keys}


def _validate_protocol_bindings(a, factory_names=ALL_FACTORY_NAMES):
    """Fail fast if the selected factories' addresses form one executor-ready deployment."""
    selected = set(factory_names)
    for key in _required_address_keys(factory_names) - {"trusted_caller"}:
        if not web3.eth.get_code(a[key]):
            raise ValueError(f"{key} has no contract code: {a[key]}")

    circuit_breaker = interface.CircuitBreaker(a["circuit_breaker"])
    executor = circuit_breaker.ADMIN()
    if str(executor).lower() == "0x0000000000000000000000000000000000000000":
        raise ValueError("circuit_breaker.ADMIN is the zero address")

    def require_address(label, actual, expected):
        if str(actual).lower() != str(expected).lower():
            raise ValueError(f"{label} mismatch: {actual} != {expected}")

    if selected & OWNER_FACTORIES:
        owner = interface.LidoLendOwner(a["owner"])
        require_address("owner.LIDO_LEND", owner.LIDO_LEND(), a["core"])

        required_owner_roles = set()
        if "LidoLendActivateMarket" in selected:
            required_owner_roles.add("MARKET_CREATOR_ROLE")
        if selected & MARKET_MANAGER_FACTORIES:
            required_owner_roles.add("MARKET_MANAGER_ROLE")
        if selected & GUARDIAN_MANAGER_FACTORIES:
            required_owner_roles.add("GUARDIAN_MANAGER_ROLE")
        for role_name in required_owner_roles:
            role = web3.keccak(text=role_name)
            if not owner.hasRole(role, executor):
                raise ValueError(f"executor lacks owner.{role_name}: {executor}")

    if selected & IRM_ROUTER_FACTORIES:
        irm_router = interface.IrmRouter(a["irm_router"])
        require_address("irm_router.MORPHO", irm_router.MORPHO(), a["core"])
        if selected & IRM_ROUTER_TARGET_FACTORIES:
            require_address("irm_router.manager", irm_router.manager(), executor)

    if selected & ADAPTIVE_CURVE_IRM_FACTORIES:
        adaptive_curve_irm = interface.AdaptiveCurveIrm(a["adaptive_curve_irm"])
        require_address("adaptive_curve_irm.ROUTER", adaptive_curve_irm.ROUTER(), a["irm_router"])
        require_address("adaptive_curve_irm.manager", adaptive_curve_irm.manager(), executor)

    if selected & RISK_STEWARD_FACTORIES:
        risk_steward_dashboard = interface.RiskStewardDashboard(a["risk_steward_dashboard"])
        require_address(
            "risk_steward_dashboard.LIDO_LEND",
            risk_steward_dashboard.LIDO_LEND(),
            a["core"],
        )
        steward_admin_role = web3.keccak(text="STEWARD_ADMIN_ROLE")
        if not risk_steward_dashboard.hasRole(steward_admin_role, executor):
            raise ValueError(f"executor lacks risk_steward_dashboard.STEWARD_ADMIN_ROLE: {executor}")

    if selected & EXIT_BOOK_FACTORIES:
        morpho_exit_book = interface.MorphoExitBook(a["morpho_exit_book"])
        erc4626_exit_book = interface.Erc4626ExitBook(a["erc4626_exit_book"])
        require_address("morpho_exit_book.MORPHO", morpho_exit_book.MORPHO(), a["core"])

        allowlist_manager_role = web3.keccak(text="ALLOWLIST_MANAGER_ROLE")
        for label, exit_book in (
            ("morpho_exit_book", morpho_exit_book),
            ("erc4626_exit_book", erc4626_exit_book),
        ):
            if not exit_book.hasRole(allowlist_manager_role, executor):
                raise ValueError(f"executor lacks {label}.ALLOWLIST_MANAGER_ROLE: {executor}")

    return executor


def _deployment_plan(a, factory_names=ALL_FACTORY_NAMES):
    "Maps each selected factory to its constructor args, from the resolved address dict `a`."
    selected = set(factory_names)
    tc = a["trusted_caller"]
    core = a["core"]
    plan = []

    def add(Factory, args):
        if Factory._name in selected:
            plan.append((Factory, args))

    add(
        LidoLendActivateMarket,
        lambda: [tc, a["owner"], a["irm_router"], a["adaptive_curve_irm"], a["circuit_breaker"]],
    )
    # Market/guardian management routes through the LidoLendOwner facade (fixed EVMScript target); the
    # factories derive the core from `owner.LIDO_LEND()` for validation.
    for Factory in (
        LidoLendAddGuardian,
        LidoLendRemoveGuardian,
        LidoLendReplaceGuardian,
        LidoLendGrantInstantActivation,
        LidoLendSetGuardiansQuorum,
        LidoLendSetSuspectWindow,
        LidoLendUnbanGuardianSignals,
        LidoLendSetCollateralActivationConfig,
        LidoLendSetSettlementConfig,
        LidoLendSetSupplyCap,
        LidoLendUnfreezeMarket,
    ):
        add(Factory, lambda: [tc, a["owner"]])
    # IRM management targets the configured router / AdaptiveCurveIrm singletons directly.
    add(
        LidoLendSetIrmCurveParams,
        lambda: [tc, core, a["irm_router"], a["adaptive_curve_irm"]],
    )
    add(LidoLendSetMarketIrm, lambda: [tc, core, a["irm_router"]])
    add(LidoLendAddRiskSteward, lambda: [tc, core, a["risk_steward_dashboard"]])
    add(LidoLendRemoveRiskSteward, lambda: [tc, core, a["risk_steward_dashboard"]])
    add(
        LidoLendSetMarketExitBookAllowed,
        lambda: [tc, a["morpho_exit_book"], a["erc4626_exit_book"]],
    )
    return [(Factory, args()) for Factory, args in plan]


def _permission(*calls):
    """Encode EasyTrack permissions as concatenated (target address ++ selector) entries."""
    return "0x" + "".join(str(getattr(target, "address", target))[2:] + selector[2:] for target, selector in calls)


def _permissions_plan(a, factory_names=ALL_FACTORY_NAMES):
    """Return the fixed EasyTrack permission blob for each selected factory."""
    selected = set(factory_names)
    permissions = {}

    if selected & OWNER_FACTORIES:
        owner = interface.LidoLendOwner(a["owner"])
    if selected & IRM_ROUTER_FACTORIES:
        irm_router = interface.IrmRouter(a["irm_router"])
    if selected & ADAPTIVE_CURVE_IRM_FACTORIES:
        adaptive_curve_irm = interface.AdaptiveCurveIrm(a["adaptive_curve_irm"])
    if "LidoLendActivateMarket" in selected:
        circuit_breaker = interface.CircuitBreaker(a["circuit_breaker"])
        controlled_market_create_selector = (
            "0x" + web3.keccak(text="createMarket((address,address,address,address,uint256),address,bool)").hex()[2:10]
        )
        permissions["LidoLendActivateMarket"] = _permission(
            (adaptive_curve_irm, adaptive_curve_irm.setMarketCurveParams.signature),
            (irm_router, irm_router.setMarketIrm.signature),
            (owner, controlled_market_create_selector),
            (circuit_breaker, circuit_breaker.registerPauser.signature),
        )
    if "LidoLendAddGuardian" in selected:
        permissions["LidoLendAddGuardian"] = _permission((owner, owner.addGuardian.signature))
    if "LidoLendRemoveGuardian" in selected:
        permissions["LidoLendRemoveGuardian"] = _permission((owner, owner.removeGuardian.signature))
    if "LidoLendReplaceGuardian" in selected:
        permissions["LidoLendReplaceGuardian"] = _permission(
            (owner, owner.removeGuardian.signature),
            (owner, owner.addGuardian.signature),
        )
    if "LidoLendGrantInstantActivation" in selected:
        permissions["LidoLendGrantInstantActivation"] = _permission(
            (owner, owner.grantMarketInstantActivation.signature)
        )
    if "LidoLendSetGuardiansQuorum" in selected:
        permissions["LidoLendSetGuardiansQuorum"] = _permission((owner, owner.setGuardiansQuorum.signature))
    if "LidoLendSetSuspectWindow" in selected:
        permissions["LidoLendSetSuspectWindow"] = _permission((owner, owner.setGuardiansSuspectWindow.signature))
    if "LidoLendUnbanGuardianSignals" in selected:
        permissions["LidoLendUnbanGuardianSignals"] = _permission((owner, owner.unbanGuardianSignals.signature))
    if "LidoLendSetCollateralActivationConfig" in selected:
        permissions["LidoLendSetCollateralActivationConfig"] = _permission(
            (owner, owner.setMarketCollateralActivationConfig.signature)
        )
    if "LidoLendSetSettlementConfig" in selected:
        permissions["LidoLendSetSettlementConfig"] = _permission((owner, owner.setMarketSettlementConfig.signature))
    if "LidoLendSetSupplyCap" in selected:
        permissions["LidoLendSetSupplyCap"] = _permission((owner, owner.setMarketSupplyCap.signature))
    if "LidoLendUnfreezeMarket" in selected:
        permissions["LidoLendUnfreezeMarket"] = _permission((owner, owner.unfreezeMarket.signature))
    if "LidoLendSetIrmCurveParams" in selected:
        permissions["LidoLendSetIrmCurveParams"] = _permission(
            (adaptive_curve_irm, adaptive_curve_irm.setMarketCurveParams.signature)
        )
    if "LidoLendSetMarketIrm" in selected:
        permissions["LidoLendSetMarketIrm"] = _permission((irm_router, irm_router.setMarketIrm.signature))
    if selected & RISK_STEWARD_FACTORIES:
        risk_steward_dashboard = interface.RiskStewardDashboard(a["risk_steward_dashboard"])
    if "LidoLendAddRiskSteward" in selected:
        permissions["LidoLendAddRiskSteward"] = _permission(
            (risk_steward_dashboard, risk_steward_dashboard.addMarketSteward.signature)
        )
    if "LidoLendRemoveRiskSteward" in selected:
        permissions["LidoLendRemoveRiskSteward"] = _permission(
            (risk_steward_dashboard, risk_steward_dashboard.removeMarketSteward.signature)
        )
    if selected & EXIT_BOOK_FACTORIES:
        morpho_exit_book = interface.MorphoExitBook(a["morpho_exit_book"])
        erc4626_exit_book = interface.Erc4626ExitBook(a["erc4626_exit_book"])
        permissions["LidoLendSetMarketExitBookAllowed"] = _permission(
            (morpho_exit_book, morpho_exit_book.setMarketAllowed.signature),
            (erc4626_exit_book, erc4626_exit_book.setVaultAllowed.signature),
        )
    return permissions


def deploy_lido_lend_factories(addresses, tx_params, factory_names=ALL_FACTORY_NAMES):
    "Deploy selected factories and return artifacts including constructor args and permissions."
    artifacts = {}
    instances = []
    permissions = _permissions_plan(addresses, factory_names)
    for Factory, args in _deployment_plan(addresses, factory_names):
        instance = Factory.deploy(*args, tx_params)
        name = Factory._name
        artifacts[name] = {
            "contract": name,
            "address": instance.address,
            "constructorArgs": args,
            "permissions": permissions[name],
        }
        instances.append((Factory, instance))
        log.ok(f"Deployed {name}", instance.address)
    return artifacts, instances


def main():
    network_name = get_network_name()
    factory_names = _parse_factory_selection(os.environ.get("LIDO_LEND_FACTORIES"))
    addresses = _read_addresses(factory_names)
    executor = _validate_protocol_bindings(addresses, factory_names)
    deployer = get_deployer_account(get_is_live(), network=network_name)

    log.br()
    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("EVMScriptExecutor", executor)
    log.ok("Factories", ", ".join(name.removeprefix("LidoLend") for name in factory_names))
    log.br()
    for key, value in addresses.items():
        log.nb(key, value)
    log.br()

    print("Proceed? [yes/no]: ")
    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "300 gwei"

    artifacts, instances = deploy_lido_lend_factories(addresses, tx_params, factory_names)

    filename = f"et-lido-lend-deployed-{network_name}-{chain.id}-{chain.height}.json"
    with open(filename, "x") as outfile:
        json.dump(artifacts, outfile, indent=2)
    log.br()
    log.ok("Deployment artifacts saved to", filename)

    if get_is_live():
        log.br()
        log.ok("Publishing sources...")
        for Factory, instance in instances:
            Factory.publish_source(instance)
