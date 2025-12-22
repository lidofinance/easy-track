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

from utils.constants import get_network_config


def main():
    network_name = get_network_name()

    # Get Lido addresses
    addresses = lido.addresses(network=network_name)
    lido_locator = addresses.locator
    # Get deployer account
    deployer = get_deployer_account(get_is_live(), network=network_name)
    # Get network config
    config = get_network_config(network_name)

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Etherscan API Key", os.getenv("ETHERSCAN_TOKEN"))

    log.br()

    log.nb("stVaults Committee", config.st_vaults_committee)
    log.nb("Deployed Lido Locator", lido_locator)
    log.nb("Max group share limit (Phase 1)", config.max_group_share_limit_phase_1)
    log.nb("Max default tier share limit (Phase 1)", config.max_default_tier_share_limit_phase_1)
    log.nb("Max group share limit (Phase 2 and 3)", config.max_group_share_limit_phase_2_and_3)
    log.nb("Max default tier share limit (Phase 2 and 3)", config.max_default_tier_share_limit_phase_2_and_3)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "10 gwei"

    deploy_operator_grid_factories(
        network_name,
        config,
        lido_locator,
        tx_params,
    )


def deploy_operator_grid_factories(
    network_name,
    config,
    lido_locator,
    tx_params,
):
    deployment_artifacts = {}

    # RegisterGroupsInOperatorGrid (Phase 1)
    register_groups_in_operator_grid_1 = RegisterGroupsInOperatorGrid.deploy(
        config.st_vaults_committee,
        lido_locator,
        config.max_group_share_limit_phase_1,
        tx_params,
    )
    deployment_artifacts["RegisterGroupsInOperatorGrid (Phase 1)"] = {
        "contract": "RegisterGroupsInOperatorGrid",
        "address": register_groups_in_operator_grid_1.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator, config.max_group_share_limit_phase_1],
    }

    log.ok("Deployed RegisterGroupsInOperatorGrid (Phase 1)", register_groups_in_operator_grid_1.address)

    # RegisterGroupsInOperatorGrid (Phase 2 and 3)
    register_groups_in_operator_grid_2 = RegisterGroupsInOperatorGrid.deploy(
        config.st_vaults_committee,
        lido_locator,
        config.max_group_share_limit_phase_2_and_3,
        tx_params,
    )
    deployment_artifacts["RegisterGroupsInOperatorGrid (Phase 2 and 3)"] = {
        "contract": "RegisterGroupsInOperatorGrid",
        "address": register_groups_in_operator_grid_2.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator, config.max_group_share_limit_phase_2_and_3],
    }

    log.ok("Deployed RegisterGroupsInOperatorGrid (Phase 2 and 3)", register_groups_in_operator_grid_2.address)

    # UpdateGroupsShareLimitInOperatorGrid (Phase 1)
    update_groups_share_limit_in_operator_grid_1 = UpdateGroupsShareLimitInOperatorGrid.deploy(
        config.st_vaults_committee,
        lido_locator,
        config.max_group_share_limit_phase_1,
        tx_params,
    )
    deployment_artifacts["UpdateGroupsShareLimitInOperatorGrid (Phase 1)"] = {
        "contract": "UpdateGroupsShareLimitInOperatorGrid",
        "address": update_groups_share_limit_in_operator_grid_1.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator, config.max_group_share_limit_phase_1],
    }

    log.ok("Deployed UpdateGroupsShareLimitInOperatorGrid (Phase 1)", update_groups_share_limit_in_operator_grid_1.address)

    # UpdateGroupsShareLimitInOperatorGrid (Phase 2 and 3)
    update_groups_share_limit_in_operator_grid_2 = UpdateGroupsShareLimitInOperatorGrid.deploy(
        config.st_vaults_committee,
        lido_locator,
        config.max_group_share_limit_phase_2_and_3,
        tx_params,
    )
    deployment_artifacts["UpdateGroupsShareLimitInOperatorGrid (Phase 2 and 3)"] = {
        "contract": "UpdateGroupsShareLimitInOperatorGrid",
        "address": update_groups_share_limit_in_operator_grid_2.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator, config.max_group_share_limit_phase_2_and_3],
    }

    log.ok("Deployed UpdateGroupsShareLimitInOperatorGrid (Phase 2 and 3)", update_groups_share_limit_in_operator_grid_2.address)

    # RegisterTiersInOperatorGrid
    register_tiers_in_operator_grid = RegisterTiersInOperatorGrid.deploy(
        config.st_vaults_committee,
        lido_locator,
        tx_params,
    )
    deployment_artifacts["RegisterTiersInOperatorGrid"] = {
        "contract": "RegisterTiersInOperatorGrid",
        "address": register_tiers_in_operator_grid.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator],
    }

    log.ok("Deployed RegisterTiersInOperatorGrid", register_tiers_in_operator_grid.address)

    # AlterTiersInOperatorGrid (Phase 1)
    alter_tiers_in_operator_grid_1 = AlterTiersInOperatorGrid.deploy(
        config.st_vaults_committee,
        lido_locator,
        config.max_default_tier_share_limit_phase_1,
        tx_params,
    )
    deployment_artifacts["AlterTiersInOperatorGrid (Phase 1)"] = {
        "contract": "AlterTiersInOperatorGrid",
        "address": alter_tiers_in_operator_grid_1.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator, config.max_default_tier_share_limit_phase_1],
    }

    log.ok("Deployed AlterTiersInOperatorGrid (Phase 1)", alter_tiers_in_operator_grid_1.address)

    # AlterTiersInOperatorGrid (Phase 2 and 3)
    alter_tiers_in_operator_grid_2 = AlterTiersInOperatorGrid.deploy(
        config.st_vaults_committee,
        lido_locator,
        config.max_default_tier_share_limit_phase_2_and_3,
        tx_params,
    )
    deployment_artifacts["AlterTiersInOperatorGrid (Phase 2 and 3)"] = {
        "contract": "AlterTiersInOperatorGrid",
        "address": alter_tiers_in_operator_grid_2.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator, config.max_default_tier_share_limit_phase_2_and_3],
    }

    log.ok("Deployed AlterTiersInOperatorGrid (Phase 2 and 3)", alter_tiers_in_operator_grid_2.address)

    log.br()
    log.ok(f"All base vaults factories have been deployed. Saving artifacts...")

    filename = f"et-base-vaults-deployed-{network_name}.json"

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
    log.ok("All base vaultsfactories have been verified and published.")
