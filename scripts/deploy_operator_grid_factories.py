import json
import os

from brownie import (
    chain,
    network,
    RegisterGroupsInOperatorGrid,
    UpdateGroupsShareLimitInOperatorGrid,
    RegisterTiersInOperatorGrid,
    AlterTiersInOperatorGrid,
    web3,
)

from utils import lido, log, deployment
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

    addresses = lido.addresses(network=network_name)
    deployer = get_deployer_account(get_is_live(), network=network_name)
    trusted_caller = get_trusted_caller()

    operator_grid = addresses.operator_grid

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.br()

    log.nb("Deployed Operator Grid", operator_grid)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "300 gwei"

    deploy_operator_grid_factories(
        network_name,
        trusted_caller,
        operator_grid,
        tx_params,
    )


def deploy_operator_grid_factories(
    network_name,
    trusted_caller,
    operator_grid,
    tx_params,
):
    deployment_artifacts = {}

    # RegisterGroupsInOperatorGrid
    register_groups_in_operator_grid = RegisterGroupsInOperatorGrid.deploy(
        trusted_caller,
        operator_grid,
        tx_params,
    )
    deployment_artifacts["RegisterGroupsInOperatorGrid"] = {
        "contract": "RegisterGroupsInOperatorGrid",
        "address": register_groups_in_operator_grid.address,
        "constructorArgs": [trusted_caller, operator_grid],
    }

    log.ok("Deployed RegisterGroupsInOperatorGrid", register_groups_in_operator_grid.address)

    # UpdateGroupsShareLimitInOperatorGrid
    update_groups_share_limit_in_operator_grid = UpdateGroupsShareLimitInOperatorGrid.deploy(
        trusted_caller,
        operator_grid,
        tx_params,
    )
    deployment_artifacts["UpdateGroupsShareLimitInOperatorGrid"] = {
        "contract": "UpdateGroupsShareLimitInOperatorGrid",
        "address": update_groups_share_limit_in_operator_grid.address,
        "constructorArgs": [trusted_caller, operator_grid],
    }

    log.ok("Deployed UpdateGroupsShareLimitInOperatorGrid", update_groups_share_limit_in_operator_grid.address)

    # RegisterTiersInOperatorGrid
    register_tiers_in_operator_grid = RegisterTiersInOperatorGrid.deploy(
        trusted_caller,
        operator_grid,
        tx_params,
    )
    deployment_artifacts["RegisterTiersInOperatorGrid"] = {
        "contract": "RegisterTiersInOperatorGrid",
        "address": register_tiers_in_operator_grid.address,
        "constructorArgs": [trusted_caller, operator_grid],
    }

    log.ok("Deployed RegisterTiersInOperatorGrid", register_tiers_in_operator_grid.address)

    # AlterTiersInOperatorGrid
    alter_tiers_in_operator_grid = AlterTiersInOperatorGrid.deploy(
        trusted_caller,
        operator_grid,
        tx_params,
    )
    deployment_artifacts["AlterTiersInOperatorGrid"] = {
        "contract": "AlterTiersInOperatorGrid",
        "address": alter_tiers_in_operator_grid.address,
        "constructorArgs": [trusted_caller, operator_grid],
    }

    log.ok("Deployed AlterTiersInOperatorGrid", alter_tiers_in_operator_grid.address)

    log.br()
    log.ok(f"All Operator Grid factories have been deployed. Saving artifacts...")

    filename = f"et-operator-grid-deployed-{network_name}.json"

    with open(filename, "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.br()
    log.ok("Deployment artifacts have been saved to", filename)

    RegisterGroupsInOperatorGrid.publish_source(register_groups_in_operator_grid)
    UpdateGroupsShareLimitInOperatorGrid.publish_source(update_groups_share_limit_in_operator_grid)
    RegisterTiersInOperatorGrid.publish_source(register_tiers_in_operator_grid)
    AlterTiersInOperatorGrid.publish_source(alter_tiers_in_operator_grid)

    log.br()
    log.ok("All Operator Grid factories have been verified and published.")
