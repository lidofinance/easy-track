import json
import os

from brownie import (
    chain,
    SettleGeneralDelayedPenalty,
    web3,
)

from utils import cm, log
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


def get_factory_name():
    if "FACTORY_NAME" not in os.environ:
        raise EnvironmentError("Please set FACTORY_NAME env variable")

    factory_name = os.environ["FACTORY_NAME"]

    if not factory_name:
        raise ValueError("Factory name cannot be empty")
    if not isinstance(factory_name, str):
        raise TypeError("Factory name must be a string")

    return factory_name


def main():
    network_name = get_network_name()
    cm_contracts = cm.contracts(network=network_name)

    deployer = get_deployer_account(get_is_live(), network=network_name)
    trusted_caller = get_trusted_caller()
    factory_name = get_factory_name()
    module = cm_contracts.module

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("Trusted caller", trusted_caller)
    log.ok("Factory name", factory_name)
    log.ok("Module address", module)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return


    log.br()

    deployment_artifacts = {}

    # SettleGeneralDelayedPenalty
    settle_general_delayed_penalty = SettleGeneralDelayedPenalty.deploy(
        trusted_caller, module.address, {"from": deployer}
    )
    deployment_artifacts["SettleGeneralDelayedPenalty"] = {
        "contract": "SettleGeneralDelayedPenalty",
        "address": settle_general_delayed_penalty.address,
        "constructorArgs": [trusted_caller, module.address],
    }

    log.ok("Deployed SettleGeneralDelayedPenalty", settle_general_delayed_penalty.address)

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving artifacts...")

    with open(f"deployed-cm-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.nb("Starting code verification.")
    log.br()

    SettleGeneralDelayedPenalty.publish_source(settle_general_delayed_penalty)

    log.br()
