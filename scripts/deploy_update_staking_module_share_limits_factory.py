import json
import os

from brownie import chain, web3, UpdateStakingModuleShareLimits

from utils import log
from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)


def _required_env(name: str) -> str:
    if name not in os.environ:
        raise EnvironmentError(f"Please set {name} env variable")
    val = os.environ[name]
    if not val:
        raise ValueError(f"Environment variable {name} is empty")
    return val


def _get_trusted_caller() -> str:
    trusted_caller = _required_env("TRUSTED_CALLER")
    assert web3.is_address(trusted_caller), "Trusted caller address is not valid"
    return trusted_caller


def _get_factory_name() -> str:
    factory_name = _required_env("FACTORY_NAME")
    if not isinstance(factory_name, str):
        raise TypeError("Factory name must be a string")
    return factory_name


def _get_staking_router() -> str:
    staking_router = _required_env("STAKING_ROUTER")
    assert web3.is_address(staking_router), "StakingRouter address is not valid"
    return staking_router


def _get_module_id() -> int:
    return int(_required_env("STAKING_MODULE_ID"))


def _get_limit_bp(var: str) -> int:
    value = int(_required_env(var))
    if value < 0:
        raise ValueError(f"{var} must be non-negative")
    return value


def main():
    network_name = get_network_name()
    is_live = get_is_live()

    deployer = get_deployer_account(is_live, network=network_name)
    trusted_caller = _get_trusted_caller()
    factory_name = _get_factory_name()
    staking_router = _get_staking_router()
    staking_module_id = _get_module_id()
    max_stake_share_increase = _get_limit_bp("MAX_STAKE_SHARE_LIMIT_INCREASE_BP")
    max_stake_share_decrease = _get_limit_bp("MAX_STAKE_SHARE_LIMIT_DECREASE_BP")
    max_priority_threshold_increase = _get_limit_bp("MAX_PRIORITY_EXIT_SHARE_THRESHOLD_INCREASE_BP")
    max_priority_threshold_decrease = _get_limit_bp("MAX_PRIORITY_EXIT_SHARE_THRESHOLD_DECREASE_BP")

    log.br()
    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("chain id", chain.id)

    log.br()
    log.ok("Deployer", deployer)
    log.ok("Trusted caller", trusted_caller)
    log.ok("Factory name", factory_name)
    log.ok("StakingRouter", staking_router)
    log.ok("Staking module id", staking_module_id)
    log.ok("Max stake share increase bp", max_stake_share_increase)
    log.ok("Max stake share decrease bp", max_stake_share_decrease)
    log.ok("Priority exit threshold +bp", max_priority_threshold_increase)
    log.ok("Priority exit threshold -bp", max_priority_threshold_decrease)

    log.br()
    print("Proceed? [yes/no]: ")
    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if is_live:
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "50 gwei"

    log.br()
    log.nb("Deploying UpdateStakingModuleShareLimits...")

    factory = UpdateStakingModuleShareLimits.deploy(
        trusted_caller,
        factory_name,
        staking_router,
        staking_module_id,
        max_stake_share_increase,
        max_stake_share_decrease,
        max_priority_threshold_increase,
        max_priority_threshold_decrease,
        tx_params,
    )

    log.ok("Deployed UpdateStakingModuleShareLimits", factory.address)

    entry_key = f"UpdateStakingModuleShareLimits:{factory_name}"
    deployment_artifacts = {
        entry_key: {
            "contract": "UpdateStakingModuleShareLimits",
            "address": factory.address,
            "constructorArgs": [
                trusted_caller,
                factory_name,
                staking_router,
                staking_module_id,
                max_stake_share_increase,
                max_stake_share_decrease,
                max_priority_threshold_increase,
                max_priority_threshold_decrease,
            ],
            "txHash": factory.tx.txid,
        }
    }

    artifacts_path = f"deployed-sr-{network_name}.json"
    if os.path.exists(artifacts_path):
        with open(artifacts_path, "r") as previous_artifacts:
            existing_artifacts = json.load(previous_artifacts)
        existing_artifacts.update(deployment_artifacts)
        deployment_artifacts = existing_artifacts

    with open(artifacts_path, "w") as outfile:
        json.dump(deployment_artifacts, outfile, indent=4)

    log.br()
    log.nb("Artifacts saved to", artifacts_path)

    if is_live and get_env("FORCE_VERIFY", False):
        log.nb("Starting code verification.")
        log.br()
        UpdateStakingModuleShareLimits.publish_source(factory)

    log.br()
