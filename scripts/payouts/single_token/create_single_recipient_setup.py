from brownie import chain, network

from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
)
from utils import lido, log, deployment
from scripts.payouts.single_token.acceptance_test_single_setup import main as run_acceptance_test


deploy_config = deployment.AllowedRecipientsSingleTokenSingleRecipientSetupDeployConfig(
    period=3,
    spent_amount=0,
    title="Test funder",
    limit=2000 * 10**18,
    token="0x6B175474E89094C44Da98b954EedeAC495271d0F",
    trusted_caller="0x606f77BF3dd6Ed9790D9771C7003f269a385D942",
)

def main():
    network_name = network.show_active()
    deployer = get_deployer_account(get_is_live(), network=network_name)
    allowed_recipients_builder = lido.allowed_recipients_builder_single_token(network=network_name)

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

    registryAddress = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    topUpAddress = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]

    log.ok("Allowed recipients easy track contracts have been deployed...")
    log.nb("Deployed AllowedRecipientsRegistryDeployed", registryAddress)
    log.nb("Deployed TopUpAllowedRecipientsDeployed", topUpAddress)

    log.br()

    log.nb("Running acceptance test...")

    run_acceptance_test(deploy_config, tx.txid)
