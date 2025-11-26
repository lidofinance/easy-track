import json
import os
from time import sleep

from brownie import (
    chain,
    network,
    SetJailStatusInOperatorGrid,
    UpdateVaultsFeesInOperatorGrid,
    ForceValidatorExitsInVaultHub,
    SocializeBadDebtInVaultHub,
    SetLiabilitySharesTargetInVaultHub,
    VaultsAdapter,
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
    evmScriptExecutor = addresses.evm_script_executor
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
    log.nb("EVMScriptExecutor", evmScriptExecutor)
    log.nb("Deployed Lido Locator", lido_locator)
    log.nb("Initial validator exit fee limit", config.validator_exit_fee_limit)
    log.nb("Max liquidity fee BP", config.max_liquidity_fee_bp)
    log.nb("Max reservation fee BP", config.max_reservation_fee_bp)
    log.nb("Max infra fee BP", config.max_infra_fee_bp)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "10 gwei"

    deploy_vault_hub_factories(
        network_name,
        config,
        lido_locator,
        evmScriptExecutor,
        tx_params,
    )


def deploy_vault_hub_factories(
    network_name,
    config,
    lido_locator,
    evmScriptExecutor,
    tx_params,
):
    deployment_artifacts = {}

    # VaultsAdapter
    adapter = VaultsAdapter.deploy(config.st_vaults_committee, lido_locator, evmScriptExecutor, config.validator_exit_fee_limit, tx_params)
    deployment_artifacts["VaultsAdapter"] = {
        "contract": "VaultsAdapter",
        "address": adapter.address,
        "constructorArgs": [config.st_vaults_committee, lido_locator, evmScriptExecutor, config.validator_exit_fee_limit],
    }
    log.ok("Deployed VaultsAdapter", adapter.address)

    # SetJailStatusInOperatorGrid
    set_jail_status_in_operator_grid = SetJailStatusInOperatorGrid.deploy(
        config.st_vaults_committee,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["SetJailStatusInOperatorGrid"] = {
        "contract": "SetJailStatusInOperatorGrid",
        "address": set_jail_status_in_operator_grid.address,
        "constructorArgs": [config.st_vaults_committee, adapter.address],
    }

    log.ok("Deployed SetJailStatusInOperatorGrid", set_jail_status_in_operator_grid.address)

    # UpdateVaultsFeesInOperatorGrid
    update_vaults_fees_in_operator_grid = UpdateVaultsFeesInOperatorGrid.deploy(
        config.st_vaults_committee,
        adapter.address,
        lido_locator,
        config.max_liquidity_fee_bp,
        config.max_reservation_fee_bp,
        config.max_infra_fee_bp,
        tx_params,
    )
    deployment_artifacts["UpdateVaultsFeesInOperatorGrid"] = {
        "contract": "UpdateVaultsFeesInOperatorGrid",
        "address": update_vaults_fees_in_operator_grid.address,
        "constructorArgs": [config.st_vaults_committee, adapter.address, lido_locator, config.max_liquidity_fee_bp, config.max_reservation_fee_bp, config.max_infra_fee_bp],
    }

    log.ok("Deployed UpdateVaultsFeesInOperatorGrid", update_vaults_fees_in_operator_grid.address)

    # ForceValidatorExitsInVaultHub
    force_validator_exits_in_vault_hub = ForceValidatorExitsInVaultHub.deploy(
        config.st_vaults_committee,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["ForceValidatorExitsInVaultHub"] = {
        "contract": "ForceValidatorExitsInVaultHub",
        "address": force_validator_exits_in_vault_hub.address,
        "constructorArgs": [config.st_vaults_committee, adapter.address],
    }

    log.ok("Deployed ForceValidatorExitsInVaultHub", force_validator_exits_in_vault_hub.address)

    # SocializeBadDebtInVaultHub
    socialize_bad_debt_in_vault_hub = SocializeBadDebtInVaultHub.deploy(
        config.st_vaults_committee,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["SocializeBadDebtInVaultHub"] = {
        "contract": "SocializeBadDebtInVaultHub",
        "address": socialize_bad_debt_in_vault_hub.address,
        "constructorArgs": [config.st_vaults_committee, adapter.address],
    }

    log.ok("Deployed SocializeBadDebtInVaultHub", socialize_bad_debt_in_vault_hub.address)

    # SetLiabilitySharesTargetInVaultHub
    set_liability_shares_target_in_vault_hub = SetLiabilitySharesTargetInVaultHub.deploy(
        config.st_vaults_committee,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["SetLiabilitySharesTargetInVaultHub"] = {
        "contract": "SetLiabilitySharesTargetInVaultHub",
        "address": set_liability_shares_target_in_vault_hub.address,
        "constructorArgs": [config.st_vaults_committee, adapter.address],
    }

    log.ok("Deployed SetLiabilitySharesTargetInVaultHub", set_liability_shares_target_in_vault_hub.address)

    log.br()
    log.ok(f"All vaults factories with adapter have been deployed. Saving artifacts...")

    filename = f"et-vaults-factories-with-adapter-deployed-{network_name}.json"

    with open(filename, "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.br()
    log.ok("Deployment artifacts have been saved to", filename)

    VaultsAdapter.publish_source(adapter)
    sleep(2)
    SetJailStatusInOperatorGrid.publish_source(set_jail_status_in_operator_grid)
    sleep(2)
    UpdateVaultsFeesInOperatorGrid.publish_source(update_vaults_fees_in_operator_grid)
    sleep(2)
    ForceValidatorExitsInVaultHub.publish_source(force_validator_exits_in_vault_hub)
    sleep(2)
    SocializeBadDebtInVaultHub.publish_source(socialize_bad_debt_in_vault_hub)
    sleep(2)
    SetLiabilitySharesTargetInVaultHub.publish_source(set_liability_shares_target_in_vault_hub)

    log.br()
    log.ok("All vaults factories with adapter have been verified and published.")
