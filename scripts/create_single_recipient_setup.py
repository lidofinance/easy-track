from brownie import chain, network

from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)
from utils import lido, deployed_easy_track, log, deployment

from brownie import AllowedRecipientsBuilder

deploy_config = deployment.AllowedRecipientsSingleRecipientSetupDeployConfig(
    period=0,
    spent_amount=0,
    title="",
    limit=0,
    token="",
    trusted_caller="",
)


def main():
    network_name = network.show_active()
    deployer = get_deployer_account(get_is_live(), network=network_name)
    allowed_recipients_builder = lido.allowed_recipients_builder(network=network_name)

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.ok("Token", deploy_config.token)
    log.ok("Title", deploy_config.title)
    log.ok("Trusted caller", deploy_config.trusted_caller)
    log.ok("Limit", deploy_config.limit)
    log.ok("Period", deploy_config.period)
    log.ok("Spent amount", deploy_config.spent_amount)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    tx = allowed_recipients_builder.deploySingleRecipientTopUpOnlySetup(
        deploy_config.trusted_caller,
        deploy_config.title,
        deploy_config.token,
        deploy_config.limit,
        deploy_config.period,
        deploy_config.spent_amount,
        tx_params,
    )

    registryAddress = tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]
    topUpAddress = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]

    log.ok("Allowed recipients easy track contracts have been deployed...")
    log.nb("Deployed AllowedRecipientsRegistryDeployed", registryAddress)
    log.nb("Deployed TopUpAllowedRecipientsDeployed", topUpAddress)

    log.br()
