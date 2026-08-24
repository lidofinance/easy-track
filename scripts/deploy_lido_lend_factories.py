"""Deploys the Lido Lend EasyTrack factories.

Protocol addresses are read from one immutable Lido Lend deployment directory. Set:

  LIDO_LEND_ARTIFACTS_DIR - directory containing protocol.toml, markets/, and optional exit-books.toml
  TRUSTED_CALLER          - committee address allowed to create motions
  LIDO_LEND_FACTORIES     - optional comma-separated factory names; defaults to all

Before deployment the script verifies artifact consistency, that the actual EasyTrack EVMScriptExecutor
matches the protocol artifact, and that it has the roles required by the selected factories. ActivateMarket
and RegisterPauser additionally verify the shared CircuitBreaker's ADMIN. The output
artifact includes the exact fixed EasyTrack permission blob for each deployed factory.
"""

import json
import os

from brownie import (
    chain,
    interface,
    network,
    web3,
    LidoLendActivateMarket,
    LidoLendRegisterPauser,
    LidoLendAddGuardian,
    LidoLendRemoveGuardian,
    LidoLendReplaceGuardian,
    LidoLendSetInstantActivation,
    LidoLendSetGuardiansQuorum,
    LidoLendSetSuspectWindow,
    LidoLendUnbanAccount,
    LidoLendSetCollateralActivationConfig,
    LidoLendSetSettlementConfig,
    LidoLendSetSupplyCap,
    LidoLendSetFee,
    LidoLendSetFeeRecipient,
    LidoLendUnfreezeMarket,
    LidoLendSetIrmConfig,
    LidoLendSetMarketIrm,
    LidoLendAddRiskSteward,
    LidoLendRemoveRiskSteward,
    LidoLendSetMorphoExitBookAllowed,
    LidoLendSetErc4626ExitBookAllowed,
    LidoLendSetExitBooksServiceFee,
)

from utils import log
from utils.deployed_easy_track import addresses as easy_track_addresses
from utils.lido_lend_artifacts import load_lido_lend_artifacts
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


MORPHO_EXIT_BOOK_FACTORY = "LidoLendSetMorphoExitBookAllowed"
ERC4626_EXIT_BOOK_FACTORY = "LidoLendSetErc4626ExitBookAllowed"
EXIT_BOOKS_SERVICE_FEE_FACTORY = "LidoLendSetExitBooksServiceFee"

ALL_FACTORY_NAMES = (
    "LidoLendActivateMarket",
    "LidoLendRegisterPauser",
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
    "LidoLendSetIrmConfig",
    "LidoLendSetMarketIrm",
    "LidoLendAddRiskSteward",
    "LidoLendRemoveRiskSteward",
    MORPHO_EXIT_BOOK_FACTORY,
    ERC4626_EXIT_BOOK_FACTORY,
    EXIT_BOOKS_SERVICE_FEE_FACTORY,
)

MARKET_MANAGER_FACTORIES = {
    "LidoLendSetInstantActivation",
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
    "LidoLendUnbanAccount",
}
FEE_MANAGER_FACTORIES = {"LidoLendActivateMarket", "LidoLendSetFee", "LidoLendSetFeeRecipient"}
OWNER_FACTORIES = (
    {"LidoLendActivateMarket"} | MARKET_MANAGER_FACTORIES | GUARDIAN_MANAGER_FACTORIES | FEE_MANAGER_FACTORIES
)
IRM_ROUTER_FACTORIES = {
    "LidoLendActivateMarket",
    "LidoLendSetIrmConfig",
    "LidoLendSetMarketIrm",
}
IRM_ROUTER_TARGET_FACTORIES = {
    "LidoLendActivateMarket",
    "LidoLendSetMarketIrm",
}
ADAPTIVE_CURVE_IRM_FACTORIES = {
    "LidoLendActivateMarket",
    "LidoLendSetIrmConfig",
}
RISK_STEWARD_FACTORIES = {
    "LidoLendActivateMarket",
    "LidoLendAddRiskSteward",
    "LidoLendRemoveRiskSteward",
}
CIRCUIT_BREAKER_FACTORIES = {"LidoLendActivateMarket", "LidoLendRegisterPauser"}
EXIT_BOOK_FACTORIES = {
    MORPHO_EXIT_BOOK_FACTORY,
    ERC4626_EXIT_BOOK_FACTORY,
    EXIT_BOOKS_SERVICE_FEE_FACTORY,
}


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
    keys = {"trusted_caller", "core"}
    if selected & CIRCUIT_BREAKER_FACTORIES:
        keys.add("circuit_breaker")
    if selected & OWNER_FACTORIES:
        keys.add("owner")
    if selected & IRM_ROUTER_FACTORIES:
        keys.add("irm_router")
    if selected & ADAPTIVE_CURVE_IRM_FACTORIES:
        keys.add("adaptive_curve_irm")
    if selected & RISK_STEWARD_FACTORIES:
        keys.add("risk_steward_dashboard")
    if MORPHO_EXIT_BOOK_FACTORY in selected or EXIT_BOOKS_SERVICE_FEE_FACTORY in selected:
        keys.add("morpho_exit_book")
    if ERC4626_EXIT_BOOK_FACTORY in selected or EXIT_BOOKS_SERVICE_FEE_FACTORY in selected:
        keys.add("erc4626_exit_book")
    return keys


def _read_addresses(factory_names, artifacts_dir=None):
    required_keys = _required_address_keys(factory_names)
    if artifacts_dir is None:
        artifacts_dir = os.environ.get("LIDO_LEND_ARTIFACTS_DIR")
    if not artifacts_dir:
        raise EnvironmentError("Please set LIDO_LEND_ARTIFACTS_DIR env variable")

    deployment = load_lido_lend_artifacts(
        artifacts_dir,
        require_exit_books=bool(set(factory_names) & EXIT_BOOK_FACTORIES),
    )
    artifact_chain_id = int(deployment["metadata"]["chain_id"])
    if artifact_chain_id != chain.id:
        raise ValueError(f"artifact chain id {artifact_chain_id} does not match connected chain id {chain.id}")

    protocol = deployment["protocol"]["protocol"]
    available = {
        "trusted_caller": _env_address("TRUSTED_CALLER"),
        "core": protocol["core"],
        "owner": protocol["owner_facade"],
        "irm_router": protocol["irm_router"],
        "adaptive_curve_irm": protocol["adaptive_curve_irm"],
        "risk_steward_dashboard": protocol["risk_steward_dashboard"],
        "circuit_breaker": protocol["circuit_breaker"],
        "evm_script_executor": protocol["evm_script_executor"],
    }
    if required_keys & {"morpho_exit_book", "erc4626_exit_book"}:
        exit_books = deployment["exit_books"]["exit_books"]
        if "morpho_exit_book" in required_keys:
            available["morpho_exit_book"] = exit_books["morpho"]
        if "erc4626_exit_book" in required_keys:
            available["erc4626_exit_book"] = exit_books["erc4626"]

    return {key: value for key, value in available.items() if key in required_keys or key == "evm_script_executor"}


def _easy_track_executor(network_name):
    easy_track = easy_track_addresses(network_name)
    return interface.IEasyTrack(easy_track.easy_track).evmScriptExecutor()


def _validate_protocol_bindings(a, expected_executor, factory_names=ALL_FACTORY_NAMES):
    """Fail fast if the selected factories' addresses form one executor-ready deployment."""
    selected = set(factory_names)
    executor = expected_executor
    artifact_executor = a.get("evm_script_executor", expected_executor)
    if str(artifact_executor).lower() != str(expected_executor).lower():
        raise ValueError(
            "protocol artifact executor does not match EasyTrack evmScriptExecutor: "
            f"{artifact_executor} != {expected_executor}"
        )
    if selected & CIRCUIT_BREAKER_FACTORIES:
        circuit_breaker = interface.CircuitBreaker(a["circuit_breaker"])
        circuit_breaker_admin = circuit_breaker.ADMIN()
        if str(circuit_breaker_admin).lower() == "0x0000000000000000000000000000000000000000":
            raise ValueError("circuit_breaker.ADMIN is the zero address")
        if str(circuit_breaker_admin).lower() != str(executor).lower():
            raise ValueError(
                "circuit_breaker.ADMIN does not match EasyTrack evmScriptExecutor: "
                f"{circuit_breaker_admin} != {executor}"
            )

    def require_address(label, actual, expected):
        if str(actual).lower() != str(expected).lower():
            raise ValueError(f"{label} mismatch: {actual} != {expected}")

    if selected & OWNER_FACTORIES:
        core = interface.LidoLend(a["core"])
        owner = interface.LidoLendOwner(a["owner"])
        require_address("owner.LIDO_LEND", owner.LIDO_LEND(), a["core"])
        require_address("core.owner", core.owner(), a["owner"])

        required_owner_roles = set()
        if "LidoLendActivateMarket" in selected:
            required_owner_roles.add("MARKET_CREATOR_ROLE")
        if selected & MARKET_MANAGER_FACTORIES:
            required_owner_roles.add("MARKET_MANAGER_ROLE")
        if selected & GUARDIAN_MANAGER_FACTORIES:
            required_owner_roles.add("GUARDIAN_MANAGER_ROLE")
        if selected & FEE_MANAGER_FACTORIES:
            required_owner_roles.add("FEE_MANAGER_ROLE")
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
        allowlist_manager_role = web3.keccak(text="ALLOWLIST_MANAGER_ROLE")
        fee_manager_role = web3.keccak(text="FEE_MANAGER_ROLE")

    if MORPHO_EXIT_BOOK_FACTORY in selected or EXIT_BOOKS_SERVICE_FEE_FACTORY in selected:
        morpho_exit_book = interface.MorphoExitBook(a["morpho_exit_book"])
        require_address("morpho_exit_book.MORPHO", morpho_exit_book.MORPHO(), a["core"])
        if MORPHO_EXIT_BOOK_FACTORY in selected and not morpho_exit_book.hasRole(allowlist_manager_role, executor):
            raise ValueError(f"executor lacks morpho_exit_book.ALLOWLIST_MANAGER_ROLE: {executor}")
        if EXIT_BOOKS_SERVICE_FEE_FACTORY in selected and not morpho_exit_book.hasRole(fee_manager_role, executor):
            raise ValueError(f"executor lacks morpho_exit_book.FEE_MANAGER_ROLE: {executor}")

    if ERC4626_EXIT_BOOK_FACTORY in selected or EXIT_BOOKS_SERVICE_FEE_FACTORY in selected:
        erc4626_exit_book = interface.Erc4626ExitBook(a["erc4626_exit_book"])
        if ERC4626_EXIT_BOOK_FACTORY in selected and not erc4626_exit_book.hasRole(allowlist_manager_role, executor):
            raise ValueError(f"executor lacks erc4626_exit_book.ALLOWLIST_MANAGER_ROLE: {executor}")
        if EXIT_BOOKS_SERVICE_FEE_FACTORY in selected and not erc4626_exit_book.hasRole(fee_manager_role, executor):
            raise ValueError(f"executor lacks erc4626_exit_book.FEE_MANAGER_ROLE: {executor}")

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
        lambda: [
            tc,
            a["owner"],
            a["irm_router"],
            a["adaptive_curve_irm"],
            a["circuit_breaker"],
            a["risk_steward_dashboard"],
        ],
    )
    add(LidoLendRegisterPauser, lambda: [tc, core, a["circuit_breaker"]])
    # Market/guardian management routes through the LidoLendOwner facade (fixed EVMScript target); the
    # factories derive the core from `owner.LIDO_LEND()` for validation.
    for Factory in (
        LidoLendAddGuardian,
        LidoLendRemoveGuardian,
        LidoLendReplaceGuardian,
        LidoLendSetInstantActivation,
        LidoLendSetGuardiansQuorum,
        LidoLendSetSuspectWindow,
        LidoLendUnbanAccount,
        LidoLendSetCollateralActivationConfig,
        LidoLendSetSettlementConfig,
        LidoLendSetSupplyCap,
        LidoLendSetFee,
        LidoLendSetFeeRecipient,
        LidoLendUnfreezeMarket,
    ):
        add(Factory, lambda: [tc, a["owner"]])
    # IRM management targets the configured router / AdaptiveCurveIrm singletons directly.
    add(
        LidoLendSetIrmConfig,
        lambda: [tc, core, a["irm_router"], a["adaptive_curve_irm"]],
    )
    add(LidoLendSetMarketIrm, lambda: [tc, core, a["irm_router"]])
    add(LidoLendAddRiskSteward, lambda: [tc, a["risk_steward_dashboard"]])
    add(LidoLendRemoveRiskSteward, lambda: [tc, a["risk_steward_dashboard"]])
    add(LidoLendSetMorphoExitBookAllowed, lambda: [tc])
    add(LidoLendSetErc4626ExitBookAllowed, lambda: [tc])
    add(LidoLendSetExitBooksServiceFee, lambda: [tc])
    return [(Factory, args()) for Factory, args in plan]


def _permission(*calls):
    """Encode EasyTrack permissions as concatenated (target address ++ selector) entries."""
    return "0x" + "".join(str(getattr(target, "address", target))[2:] + selector[2:] for target, selector in calls)


def _permissions_plan(a, factory_names=ALL_FACTORY_NAMES):
    """Return the fixed EasyTrack permission blob for each selected factory."""
    selected = set(factory_names)
    permissions = {}

    if "LidoLendSetFeeRecipient" in selected:
        core = interface.LidoLend(a["core"])
    if selected & OWNER_FACTORIES:
        owner = interface.LidoLendOwner(a["owner"])
    if selected & IRM_ROUTER_FACTORIES:
        irm_router = interface.IrmRouter(a["irm_router"])
    if selected & ADAPTIVE_CURVE_IRM_FACTORIES:
        adaptive_curve_irm = interface.AdaptiveCurveIrm(a["adaptive_curve_irm"])
    if selected & RISK_STEWARD_FACTORIES:
        risk_steward_dashboard = interface.RiskStewardDashboard(a["risk_steward_dashboard"])
    if selected & CIRCUIT_BREAKER_FACTORIES:
        circuit_breaker = interface.CircuitBreaker(a["circuit_breaker"])
    if "LidoLendActivateMarket" in selected:
        controlled_market_create_selector = (
            "0x" + web3.keccak(text="createMarket((address,address,address,address,uint256),address,bool)").hex()[2:10]
        )
        permissions["LidoLendActivateMarket"] = _permission(
            (adaptive_curve_irm, adaptive_curve_irm.applyIrmConfig.signature),
            (irm_router, irm_router.setMarketIrm.signature),
            (owner, controlled_market_create_selector),
            (risk_steward_dashboard, risk_steward_dashboard.addMarketSteward.signature),
            (circuit_breaker, circuit_breaker.registerPauser.signature),
            (owner, owner.setFee.signature),
        )
    if "LidoLendRegisterPauser" in selected:
        permissions["LidoLendRegisterPauser"] = _permission((circuit_breaker, circuit_breaker.registerPauser.signature))
    if "LidoLendAddGuardian" in selected:
        permissions["LidoLendAddGuardian"] = _permission(
            (owner, owner.addGuardian.signature),
            (owner, owner.setGuardiansQuorum.signature),
        )
    if "LidoLendRemoveGuardian" in selected:
        permissions["LidoLendRemoveGuardian"] = _permission(
            (owner, owner.setGuardiansQuorum.signature),
            (owner, owner.removeGuardian.signature),
        )
    if "LidoLendReplaceGuardian" in selected:
        permissions["LidoLendReplaceGuardian"] = _permission((owner, owner.replaceGuardian.signature))
    if "LidoLendSetInstantActivation" in selected:
        permissions["LidoLendSetInstantActivation"] = _permission((owner, owner.setInstantActivation.signature))
    if "LidoLendSetGuardiansQuorum" in selected:
        permissions["LidoLendSetGuardiansQuorum"] = _permission((owner, owner.setGuardiansQuorum.signature))
    if "LidoLendSetSuspectWindow" in selected:
        permissions["LidoLendSetSuspectWindow"] = _permission((owner, owner.setGuardiansSuspectWindow.signature))
    if "LidoLendUnbanAccount" in selected:
        permissions["LidoLendUnbanAccount"] = _permission((owner, owner.unbanGuardianSignals.signature))
    if "LidoLendSetCollateralActivationConfig" in selected:
        permissions["LidoLendSetCollateralActivationConfig"] = _permission(
            (owner, owner.setMarketCollateralActivationConfig.signature)
        )
    if "LidoLendSetSettlementConfig" in selected:
        permissions["LidoLendSetSettlementConfig"] = _permission((owner, owner.setMarketSettlementConfig.signature))
    if "LidoLendSetSupplyCap" in selected:
        permissions["LidoLendSetSupplyCap"] = _permission((owner, owner.setMarketSupplyCap.signature))
    if "LidoLendSetFee" in selected:
        permissions["LidoLendSetFee"] = _permission((owner, owner.setFee.signature))
    if "LidoLendSetFeeRecipient" in selected:
        permissions["LidoLendSetFeeRecipient"] = _permission(
            (core, core.accrueInterest.signature),
            (owner, owner.setFeeRecipient.signature),
        )
    if "LidoLendUnfreezeMarket" in selected:
        permissions["LidoLendUnfreezeMarket"] = _permission((owner, owner.unfreezeMarket.signature))
    if "LidoLendSetIrmConfig" in selected:
        permissions["LidoLendSetIrmConfig"] = _permission(
            (adaptive_curve_irm, adaptive_curve_irm.applyIrmConfig.signature)
        )
    if "LidoLendSetMarketIrm" in selected:
        permissions["LidoLendSetMarketIrm"] = _permission((irm_router, irm_router.setMarketIrm.signature))
    if "LidoLendAddRiskSteward" in selected:
        permissions["LidoLendAddRiskSteward"] = _permission(
            (risk_steward_dashboard, risk_steward_dashboard.addMarketSteward.signature)
        )
    if "LidoLendRemoveRiskSteward" in selected:
        permissions["LidoLendRemoveRiskSteward"] = _permission(
            (risk_steward_dashboard, risk_steward_dashboard.removeMarketSteward.signature)
        )
    if MORPHO_EXIT_BOOK_FACTORY in selected:
        morpho_exit_book = interface.MorphoExitBook(a["morpho_exit_book"])
        permissions[MORPHO_EXIT_BOOK_FACTORY] = _permission(
            (morpho_exit_book, morpho_exit_book.setMarketAllowed.signature)
        )
    if ERC4626_EXIT_BOOK_FACTORY in selected:
        erc4626_exit_book = interface.Erc4626ExitBook(a["erc4626_exit_book"])
        permissions[ERC4626_EXIT_BOOK_FACTORY] = _permission(
            (erc4626_exit_book, erc4626_exit_book.setVaultAllowed.signature)
        )
    if EXIT_BOOKS_SERVICE_FEE_FACTORY in selected:
        morpho_exit_book = interface.MorphoExitBook(a["morpho_exit_book"])
        erc4626_exit_book = interface.Erc4626ExitBook(a["erc4626_exit_book"])
        permissions[EXIT_BOOKS_SERVICE_FEE_FACTORY] = _permission(
            (morpho_exit_book, morpho_exit_book.setServiceFee.signature),
            (erc4626_exit_book, erc4626_exit_book.setServiceFee.signature),
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
    expected_executor = _easy_track_executor(network_name)
    executor = _validate_protocol_bindings(addresses, expected_executor, factory_names)
    deployer = get_deployer_account(get_is_live(), network=network_name)

    log.br()
    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("EVMScriptExecutor", executor)
    log.ok("Factories", ", ".join(name.removeprefix("LidoLend") for name in factory_names))
    log.ok("Lido Lend artifacts", os.environ["LIDO_LEND_ARTIFACTS_DIR"])
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
