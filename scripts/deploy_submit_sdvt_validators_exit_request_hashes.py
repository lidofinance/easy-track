import json
import os

from brownie import chain, SDVTSubmitExitRequestHashes, web3

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

    return trusted_caller


def get_sdvt_registry():
    if "SDVT_REGISTRY" not in os.environ:
        raise EnvironmentError("Please set SDVT_REGISTRY env variable")
    sdvt_registry = os.environ["SDVT_REGISTRY"]

    return sdvt_registry


def main():
    network_name = get_network_name()
    contracts = lido.contracts(network=network_name)

    deployer = get_deployer_account(get_is_live(), network=network_name)
    trusted_caller = get_trusted_caller()

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    registry = get_sdvt_registry()

    staking_router = contracts.staking_router.address
    validator_exit_bus_oracle = contracts.locator.validatorsExitBusOracle()

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("Trusted caller", trusted_caller)
    log.ok("SDVT address", registry)
    log.ok("Staking Router address", staking_router)
    log.ok("Validator Exit Bus Oracle address", validator_exit_bus_oracle)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "100 gwei"}

    log.br()

    deployment_artifacts = {}

    # SDVTSubmitExitRequestHashes
    submit_validators_exit_request_hashes = SDVTSubmitExitRequestHashes.deploy(
        trusted_caller, registry, staking_router, validator_exit_bus_oracle, tx_params
    )

    deployment_artifacts["SDVTSubmitExitRequestHashes"] = {
        "contract": "SDVTSubmitExitRequestHashes",
        "address": submit_validators_exit_request_hashes.address,
        "constructorArgs": [trusted_caller, registry, staking_router, validator_exit_bus_oracle],
    }

    log.ok("Deployed SDVTSubmitExitRequestHashes", submit_validators_exit_request_hashes.address)

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving artifacts...")

    with open(f"deployed-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.nb("Starting code verification.")
    log.br()

    SDVTSubmitExitRequestHashes.publish_source(submit_validators_exit_request_hashes)

    log.br()
