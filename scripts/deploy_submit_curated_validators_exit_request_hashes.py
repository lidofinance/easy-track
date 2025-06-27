import json
import os

from brownie import chain, CuratedSubmitExitRequestHashes, web3

from utils import lido, log
from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)


def get_node_operators_registry():
    if "NODE_OPERATORS_REGISTRY" not in os.environ:
        raise EnvironmentError("Please set NODE_OPERATORS_REGISTRY env variable")
    node_operators_registry = os.environ["NODE_OPERATORS_REGISTRY"]

    return node_operators_registry


def main():
    network_name = get_network_name()
    contracts = lido.contracts(network=network_name)

    deployer = get_deployer_account(get_is_live(), network=network_name)

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    registry = get_node_operators_registry()

    staking_router = contracts.staking_router.address
    validators_exit_bus_oracle = contracts.locator.validatorsExitBusOracle()

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("Node Operator Registry address", registry)
    log.ok("Staking Router address", staking_router)
    log.ok("Validator Exit Bus Oracle address", validators_exit_bus_oracle)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "100 gwei"}

    log.br()

    deployment_artifacts = {}

    # CuratedSubmitExitRequestHashes
    submit_validators_exit_request_hashes = CuratedSubmitExitRequestHashes.deploy(
        registry, staking_router, validators_exit_bus_oracle, tx_params
    )

    deployment_artifacts["CuratedSubmitExitRequestHashes"] = {
        "contract": "CuratedSubmitExitRequestHashes",
        "address": submit_validators_exit_request_hashes.address,
        "constructorArgs": [registry, staking_router, validators_exit_bus_oracle],
    }

    log.ok("Deployed CuratedSubmitExitRequestHashes", submit_validators_exit_request_hashes.address)

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving artifacts...")

    with open(f"deployed-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.nb("Starting code verification.")
    log.br()

    CuratedSubmitExitRequestHashes.publish_source(submit_validators_exit_request_hashes)

    log.br()
