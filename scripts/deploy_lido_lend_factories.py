"""Deploys the Lido Lend EasyTrack factories.

Draft: protocol addresses are read from environment variables (the Lido Lend backbone lives in a separate
deployment, so — unlike `lido.addresses` — there is no committed config for it yet). Set:

  TRUSTED_CALLER                     - committee address allowed to create motions (single caller for all
                                       factories in this draft; split per-committee if governance requires)
  LIDO_LEND_CORE                     - LidoLend core (OssifiableProxy hosting all markets)
  LIDO_LEND_OWNER                    - LidoLendOwner facade
  LIDO_LEND_IRM_ROUTER               - IrmRouter
  LIDO_LEND_ADAPTIVE_CURVE_IRM       - AdaptiveCurveIrm singleton
  LIDO_LEND_CIRCUIT_BREAKER          - CircuitBreaker
  LIDO_LEND_RISK_STEWARD_DASHBOARD   - RiskStewardDashboard
  LIDO_LEND_MORPHO_EXIT_BOOK         - MorphoExitBook
  LIDO_LEND_ERC4626_EXIT_BOOK        - Erc4626ExitBook
"""
import json
import os

from brownie import (
    chain,
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


def _read_addresses():
    return {
        "trusted_caller": _env_address("TRUSTED_CALLER"),
        "core": _env_address("LIDO_LEND_CORE"),
        "owner": _env_address("LIDO_LEND_OWNER"),
        "irm_router": _env_address("LIDO_LEND_IRM_ROUTER"),
        "adaptive_curve_irm": _env_address("LIDO_LEND_ADAPTIVE_CURVE_IRM"),
        "circuit_breaker": _env_address("LIDO_LEND_CIRCUIT_BREAKER"),
        "risk_steward_dashboard": _env_address("LIDO_LEND_RISK_STEWARD_DASHBOARD"),
        "morpho_exit_book": _env_address("LIDO_LEND_MORPHO_EXIT_BOOK"),
        "erc4626_exit_book": _env_address("LIDO_LEND_ERC4626_EXIT_BOOK"),
    }


def _deployment_plan(a):
    "Maps each factory to its constructor args, from the resolved address dict `a`."
    tc = a["trusted_caller"]
    core = a["core"]
    return [
        (LidoLendActivateMarket, [tc, a["owner"], a["irm_router"], a["adaptive_curve_irm"], a["circuit_breaker"]]),
        (LidoLendAddGuardian, [tc, core]),
        (LidoLendRemoveGuardian, [tc, core]),
        (LidoLendReplaceGuardian, [tc, core]),
        (LidoLendGrantInstantActivation, [tc, core]),
        (LidoLendSetGuardiansQuorum, [tc, core]),
        (LidoLendSetSuspectWindow, [tc, core]),
        (LidoLendUnbanGuardianSignals, [tc, core]),
        (LidoLendSetCollateralActivationConfig, [tc, core]),
        (LidoLendSetSettlementConfig, [tc, core]),
        (LidoLendSetSupplyCap, [tc, core]),
        (LidoLendUnfreezeMarket, [tc, core]),
        (LidoLendSetIrmCurveParams, [tc, core]),
        (LidoLendSetMarketIrm, [tc, core]),
        (LidoLendAddRiskSteward, [tc, core, a["risk_steward_dashboard"]]),
        (LidoLendRemoveRiskSteward, [tc, core, a["risk_steward_dashboard"]]),
        (LidoLendSetMarketExitBookAllowed, [tc, a["morpho_exit_book"], a["erc4626_exit_book"]]),
    ]


def deploy_lido_lend_factories(addresses, tx_params):
    "Deploys every factory per `_deployment_plan` and returns {name: {address, constructorArgs}}."
    artifacts = {}
    instances = []
    for Factory, args in _deployment_plan(addresses):
        instance = Factory.deploy(*args, tx_params)
        name = Factory._name
        artifacts[name] = {"contract": name, "address": instance.address, "constructorArgs": args}
        instances.append((Factory, instance))
        log.ok(f"Deployed {name}", instance.address)
    return artifacts, instances


def main():
    network_name = get_network_name()
    deployer = get_deployer_account(get_is_live(), network=network_name)
    addresses = _read_addresses()

    log.br()
    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
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

    artifacts, instances = deploy_lido_lend_factories(addresses, tx_params)

    filename = f"et-lido-lend-deployed-{network_name}.json"
    with open(filename, "w") as outfile:
        json.dump(artifacts, outfile, indent=2)
    log.br()
    log.ok("Deployment artifacts saved to", filename)

    if get_is_live():
        log.br()
        log.ok("Publishing sources...")
        for Factory, instance in instances:
            Factory.publish_source(instance)
