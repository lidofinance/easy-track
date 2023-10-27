import json
import os

from brownie import (
    chain,
    IncreaseNodeOperatorStakingLimit,
    web3,
)

from utils import lido, log
from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)


def main():
    network_name = get_network_name()
    contracts = lido.contracts(network=network_name)

    deployer = get_deployer_account(get_is_live(), network=network_name)
    nor_sandbox = contracts.nor_sandbox.address

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("NOR Sandbox module address", nor_sandbox)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    log.br()

    deployment_artifacts = {}

    # IncreaseNodeOperatorStakingLimit
    increase_node_operators_staking_limit_sandbox = (
        IncreaseNodeOperatorStakingLimit.deploy(nor_sandbox, tx_params)
    )
    deployment_artifacts["IncreaseNodeOperatorStakingLimitSandbox"] = {
        "contract": "IncreaseNodeOperatorStakingLimit",
        "address": increase_node_operators_staking_limit_sandbox.address,
        "constructorArgs": [nor_sandbox],
    }

    log.ok(
        "Deployed IncreaseNodeOperatorStakingLimitSandbox",
        increase_node_operators_staking_limit_sandbox.address,
    )

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving atrifacts...")

    with open(f"deployed-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.nb("Starting code verification.")
    log.br()

    IncreaseNodeOperatorStakingLimit.publish_source(
        increase_node_operators_staking_limit_sandbox
    )

    log.br()
