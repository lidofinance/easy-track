import json
import os

from brownie import (
    chain,
    network,
    DecreaseShareLimitsInVaultHub,
    DecreaseVaultsFeesInVaultHub,
    ForceValidatorExitsInVaultHub,
    SocializeBadDebtInVaultHub,
    SetVaultRedemptionsInVaultHub,
    VaultHubAdapter,
    web3,
)

from utils import lido, log, deployment
from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)

from utils.constants import INITIAL_VALIDATOR_EXIT_FEE_LIMIT


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
    evmScriptExecutor = addresses.evm_script_executor

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.br()

    log.nb("Trusted caller", trusted_caller)
    log.nb("EVMScriptExecutor", evmScriptExecutor)
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
        evmScriptExecutor,
        tx_params,
    )


def deploy_vault_hub_factories(
    network_name,
    trusted_caller,
    vault_hub,
    evmScriptExecutor,
    tx_params,
):
    deployment_artifacts = {}

    # VaultHubAdapter
    adapter = VaultHubAdapter.deploy(trusted_caller, vault_hub, evmScriptExecutor, INITIAL_VALIDATOR_EXIT_FEE_LIMIT, tx_params)
    deployment_artifacts["VaultHubAdapter"] = {
        "contract": "VaultHubAdapter",
        "address": adapter.address,
        "constructorArgs": [trusted_caller, vault_hub, evmScriptExecutor, INITIAL_VALIDATOR_EXIT_FEE_LIMIT],
    }
    log.ok("Deployed VaultHubAdapter", adapter.address)

    # DecreaseShareLimitsInVaultHub
    decrease_share_limits_in_vault_hub = DecreaseShareLimitsInVaultHub.deploy(
        trusted_caller,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["DecreaseShareLimitsInVaultHub"] = {
        "contract": "DecreaseShareLimitsInVaultHub",
        "address": decrease_share_limits_in_vault_hub.address,
        "constructorArgs": [trusted_caller, adapter.address],
    }

    log.ok("Deployed DecreaseShareLimitsInVaultHub", decrease_share_limits_in_vault_hub.address)

    # DecreaseVaultsFeesInVaultHub
    decrease_vaults_fees_in_vault_hub = DecreaseVaultsFeesInVaultHub.deploy(
        trusted_caller,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["DecreaseVaultsFeesInVaultHub"] = {
        "contract": "DecreaseVaultsFeesInVaultHub",
        "address": decrease_vaults_fees_in_vault_hub.address,
        "constructorArgs": [trusted_caller, adapter.address],
    }

    log.ok("Deployed DecreaseVaultsFeesInVaultHub", decrease_vaults_fees_in_vault_hub.address)

    # ForceValidatorExitsInVaultHub
    force_validator_exits_in_vault_hub = ForceValidatorExitsInVaultHub.deploy(
        trusted_caller,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["ForceValidatorExitsInVaultHub"] = {
        "contract": "ForceValidatorExitsInVaultHub",
        "address": force_validator_exits_in_vault_hub.address,
        "constructorArgs": [trusted_caller, adapter.address],
    }

    log.ok("Deployed ForceValidatorExitsInVaultHub", force_validator_exits_in_vault_hub.address)

    # SocializeBadDebtInVaultHub
    socialize_bad_debt_in_vault_hub = SocializeBadDebtInVaultHub.deploy(
        trusted_caller,
        adapter.address,
        tx_params,
    )
    deployment_artifacts["SocializeBadDebtInVaultHub"] = {
        "contract": "SocializeBadDebtInVaultHub",
        "address": socialize_bad_debt_in_vault_hub.address,
        "constructorArgs": [trusted_caller, adapter.address],
    }

    log.ok("Deployed SocializeBadDebtInVaultHub", socialize_bad_debt_in_vault_hub.address)

    # SetVaultRedemptionsInVaultHub
    set_vault_redemptions_in_vault_hub = SetVaultRedemptionsInVaultHub.deploy(
        trusted_caller,
        vault_hub,
        tx_params,
    )
    deployment_artifacts["SetVaultRedemptionsInVaultHub"] = {
        "contract": "SetVaultRedemptionsInVaultHub",
        "address": set_vault_redemptions_in_vault_hub.address,
        "constructorArgs": [trusted_caller, vault_hub],
    }

    log.ok("Deployed SetVaultRedemptionsInVaultHub", set_vault_redemptions_in_vault_hub.address)

    log.br()
    log.ok(f"All Vault Hub factories have been deployed. Saving artifacts...")

    filename = f"et-vault-hub-deployed-{network_name}.json"

    with open(filename, "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.br()
    log.ok("Deployment artifacts have been saved to", filename)

    VaultHubAdapter.publish_source(adapter)
    DecreaseShareLimitsInVaultHub.publish_source(decrease_share_limits_in_vault_hub)
    DecreaseVaultsFeesInVaultHub.publish_source(decrease_vaults_fees_in_vault_hub)
    ForceValidatorExitsInVaultHub.publish_source(force_validator_exits_in_vault_hub)
    SocializeBadDebtInVaultHub.publish_source(socialize_bad_debt_in_vault_hub)
    SetVaultRedemptionsInVaultHub.publish_source(set_vault_redemptions_in_vault_hub)

    log.br()
    log.ok("All Vault Hub factories have been verified and published.") 
