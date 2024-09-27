import json
import os

from brownie import chain, UpdateTargetValidatorLimits, web3

from utils import lido, log
from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)


def get_trusted_caller():
    if "TRUSTED_CALLER" not in os.environ:
        raise EnvironmentError("Please set TRUSTED_CALLER env variable")
    trusted_caller = os.environ["TRUSTED_CALLER"]

    assert web3.is_address(trusted_caller), "Trusted caller address is not valid"

    return trusted_caller


def main():
    network_name = get_network_name()
    contracts = lido.contracts(network=network_name)

    deployer = get_deployer_account(get_is_live(), network=network_name)
    trusted_caller = get_trusted_caller()
    simple_dvt = contracts.simple_dvt.address

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("Simple DVT module address", simple_dvt)
    log.ok("Trusted caller", trusted_caller)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    log.br()

    deployment_artifacts = {}

    # UpdateTargetValidatorLimits
    update_target_validator_limits = UpdateTargetValidatorLimits.deploy(
        trusted_caller, simple_dvt, tx_params
    )
    deployment_artifacts["UpdateTargetValidatorLimits"] = {
        "contract": "UpdateTargetValidatorLimits",
        "address": update_target_validator_limits.address,
        "constructorArgs": [trusted_caller, simple_dvt],
    }

    log.ok(
        "Deployed UpdateTargetValidatorLimits", update_target_validator_limits.address
    )

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving artifacts...")

    with open(f"deployed-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.nb("Starting code verification.")
    log.br()

    UpdateTargetValidatorLimits.publish_source(update_target_validator_limits)

    log.br()
