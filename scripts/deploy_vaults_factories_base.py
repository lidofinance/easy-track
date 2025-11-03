import json
import os
from time import sleep

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

from utils.constants import MAX_GROUP_SHARE_LIMIT_PHASE_1, MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_1, MAX_GROUP_SHARE_LIMIT_PHASE_2, MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_2


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

    lido_locator = addresses.locator

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.br()

    log.nb("Trusted caller", trusted_caller)
    log.nb("Deployed Lido Locator", lido_locator)
    log.nb("Max group share limit (Phase 1)", MAX_GROUP_SHARE_LIMIT_PHASE_1)
    log.nb("Max default tier share limit (Phase 1)", MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_1)
    log.nb("Max group share limit (Phase 2)", MAX_GROUP_SHARE_LIMIT_PHASE_2)
    log.nb("Max default tier share limit (Phase 2)", MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_2)

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
        lido_locator,
        tx_params,
    )


def deploy_operator_grid_factories(
    network_name,
    trusted_caller,
    lido_locator,
    tx_params,
):
    deployment_artifacts = {}

    # RegisterGroupsInOperatorGrid (Phase 1)
    register_groups_in_operator_grid_1 = RegisterGroupsInOperatorGrid.deploy(
        trusted_caller,
        lido_locator,
        MAX_GROUP_SHARE_LIMIT_PHASE_1,
        tx_params,
    )
    deployment_artifacts["RegisterGroupsInOperatorGrid (Phase 1)"] = {
        "contract": "RegisterGroupsInOperatorGrid",
        "address": register_groups_in_operator_grid_1.address,
        "constructorArgs": [trusted_caller, lido_locator, MAX_GROUP_SHARE_LIMIT_PHASE_1],
    }

    log.ok("Deployed RegisterGroupsInOperatorGrid (Phase 1)", register_groups_in_operator_grid_1.address)

    # RegisterGroupsInOperatorGrid (Phase 2)
    register_groups_in_operator_grid_2 = RegisterGroupsInOperatorGrid.deploy(
        trusted_caller,
        lido_locator,
        MAX_GROUP_SHARE_LIMIT_PHASE_2,
        tx_params,
    )
    deployment_artifacts["RegisterGroupsInOperatorGrid (Phase 2)"] = {
        "contract": "RegisterGroupsInOperatorGrid",
        "address": register_groups_in_operator_grid_2.address,
        "constructorArgs": [trusted_caller, lido_locator, MAX_GROUP_SHARE_LIMIT_PHASE_2],
    }

    log.ok("Deployed RegisterGroupsInOperatorGrid (Phase 2)", register_groups_in_operator_grid_2.address)

    # UpdateGroupsShareLimitInOperatorGrid (Phase 1)
    update_groups_share_limit_in_operator_grid_1 = UpdateGroupsShareLimitInOperatorGrid.deploy(
        trusted_caller,
        lido_locator,
        MAX_GROUP_SHARE_LIMIT_PHASE_1,
        tx_params,
    )
    deployment_artifacts["UpdateGroupsShareLimitInOperatorGrid (Phase 1)"] = {
        "contract": "UpdateGroupsShareLimitInOperatorGrid",
        "address": update_groups_share_limit_in_operator_grid_1.address,
        "constructorArgs": [trusted_caller, lido_locator, MAX_GROUP_SHARE_LIMIT_PHASE_1],
    }

    log.ok("Deployed UpdateGroupsShareLimitInOperatorGrid (Phase 1)", update_groups_share_limit_in_operator_grid_1.address)

    # UpdateGroupsShareLimitInOperatorGrid (Phase 2)
    update_groups_share_limit_in_operator_grid_2 = UpdateGroupsShareLimitInOperatorGrid.deploy(
        trusted_caller,
        lido_locator,
        MAX_GROUP_SHARE_LIMIT_PHASE_2,
        tx_params,
    )
    deployment_artifacts["UpdateGroupsShareLimitInOperatorGrid (Phase 2)"] = {
        "contract": "UpdateGroupsShareLimitInOperatorGrid",
        "address": update_groups_share_limit_in_operator_grid_2.address,
        "constructorArgs": [trusted_caller, lido_locator, MAX_GROUP_SHARE_LIMIT_PHASE_2],
    }

    log.ok("Deployed UpdateGroupsShareLimitInOperatorGrid (Phase 2)", update_groups_share_limit_in_operator_grid_2.address)

    # RegisterTiersInOperatorGrid
    register_tiers_in_operator_grid = RegisterTiersInOperatorGrid.deploy(
        trusted_caller,
        lido_locator,
        tx_params,
    )
    deployment_artifacts["RegisterTiersInOperatorGrid"] = {
        "contract": "RegisterTiersInOperatorGrid",
        "address": register_tiers_in_operator_grid.address,
        "constructorArgs": [trusted_caller, lido_locator],
    }

    log.ok("Deployed RegisterTiersInOperatorGrid", register_tiers_in_operator_grid.address)

    # AlterTiersInOperatorGrid (Phase 1)
    alter_tiers_in_operator_grid_1 = AlterTiersInOperatorGrid.deploy(
        trusted_caller,
        lido_locator,
        MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_1,
        tx_params,
    )
    deployment_artifacts["AlterTiersInOperatorGrid (Phase 1)"] = {
        "contract": "AlterTiersInOperatorGrid",
        "address": alter_tiers_in_operator_grid_1.address,
        "constructorArgs": [trusted_caller, lido_locator, MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_1],
    }

    log.ok("Deployed AlterTiersInOperatorGrid (Phase 1)", alter_tiers_in_operator_grid_1.address)

    # AlterTiersInOperatorGrid (Phase 2)
    alter_tiers_in_operator_grid_2 = AlterTiersInOperatorGrid.deploy(
        trusted_caller,
        lido_locator,
        MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_2,
        tx_params,
    )
    deployment_artifacts["AlterTiersInOperatorGrid (Phase 2)"] = {
        "contract": "AlterTiersInOperatorGrid",
        "address": alter_tiers_in_operator_grid_2.address,
        "constructorArgs": [trusted_caller, lido_locator, MAX_DEFAULT_TIER_SHARE_LIMIT_PHASE_2],
    }

    log.ok("Deployed AlterTiersInOperatorGrid (Phase 2)", alter_tiers_in_operator_grid_2.address)

    log.br()
    log.ok(f"All Operator Grid factories have been deployed. Saving artifacts...")

    filename = f"et-operator-grid-deployed-{network_name}.json"

    with open(filename, "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.br()
    log.ok("Deployment artifacts have been saved to", filename)

    RegisterGroupsInOperatorGrid.publish_source(register_groups_in_operator_grid_1)
    sleep(2)
    RegisterGroupsInOperatorGrid.publish_source(register_groups_in_operator_grid_2)
    sleep(2)
    UpdateGroupsShareLimitInOperatorGrid.publish_source(update_groups_share_limit_in_operator_grid_1)
    sleep(2)
    UpdateGroupsShareLimitInOperatorGrid.publish_source(update_groups_share_limit_in_operator_grid_2)
    sleep(2)
    RegisterTiersInOperatorGrid.publish_source(register_tiers_in_operator_grid)
    sleep(2)
    AlterTiersInOperatorGrid.publish_source(alter_tiers_in_operator_grid_1)
    sleep(2)
    AlterTiersInOperatorGrid.publish_source(alter_tiers_in_operator_grid_2)

    log.br()
    log.ok("All Operator Grid factories have been verified and published.")
