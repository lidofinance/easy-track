import json
import os

from brownie import (
    chain,
    network,
    UpdateShareLimitsInVaultHub,
    UpdateVaultsFeesInVaultHub,
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

    vault_hub = addresses.vault_hub

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.br()

    log.nb("Deployed Vault Hub", vault_hub)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "300 gwei"

    deploy_vault_hub_factories(
        network_name,
        trusted_caller,
        vault_hub,
        tx_params,
    )


def deploy_vault_hub_factories(
    network_name,
    trusted_caller,
    vault_hub,
    tx_params,
):
    deployment_artifacts = {}

    # UpdateShareLimitsInVaultHub
    update_share_limits_in_vault_hub = UpdateShareLimitsInVaultHub.deploy(
        trusted_caller,
        vault_hub,
        tx_params,
    )
    deployment_artifacts["UpdateShareLimitsInVaultHub"] = {
        "contract": "UpdateShareLimitsInVaultHub",
        "address": update_share_limits_in_vault_hub.address,
        "constructorArgs": [trusted_caller, vault_hub],
    }

    log.ok("Deployed UpdateShareLimitsInVaultHub", update_share_limits_in_vault_hub.address)

    # UpdateVaultsFeesInVaultHub
    update_vaults_fees_in_vault_hub = UpdateVaultsFeesInVaultHub.deploy(
        trusted_caller,
        vault_hub,
        tx_params,
    )
    deployment_artifacts["UpdateVaultsFeesInVaultHub"] = {
        "contract": "UpdateVaultsFeesInVaultHub",
        "address": update_vaults_fees_in_vault_hub.address,
        "constructorArgs": [trusted_caller, vault_hub],
    }

    log.ok("Deployed UpdateVaultsFeesInVaultHub", update_vaults_fees_in_vault_hub.address)

    log.br()
    log.ok(f"All Vault Hub factories have been deployed. Saving artifacts...")

    filename = f"et-vault-hub-deployed-{network_name}.json"

    with open(filename, "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.br()
    log.ok("Deployment artifacts have been saved to", filename)

    UpdateShareLimitsInVaultHub.publish_source(update_share_limits_in_vault_hub)
    UpdateVaultsFeesInVaultHub.publish_source(update_vaults_fees_in_vault_hub)

    log.br()
    log.ok("All Vault Hub factories have been verified and published.") 
