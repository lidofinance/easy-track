from brownie import chain, network

from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
)
from utils import (
    log,
    lido,
    deployment,
)
from scripts.payouts.single_token.acceptance_test_full_setup import main as run_acceptance_test


deploy_config = deployment.AllowedRecipientsSingleTokenFullSetupDeployConfig(
    token="0x6B175474E89094C44Da98b954EedeAC495271d0F",
    limit=2000 * 10**18,
    period=3,
    spent_amount=0,
    trusted_caller="0x606f77BF3dd6Ed9790D9771C7003f269a385D942",
    titles=["Test funder"],
    recipients=["0x606f77BF3dd6Ed9790D9771C7003f269a385D942"],
)


def main():
    network_name = network.show_active()
    deployer = get_deployer_account(get_is_live(), network=network_name)
    allowed_recipients_builder = lido.allowed_recipients_builder_single_token(network=network_name)

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.ok("Token", deploy_config.token)
    log.ok("Limit", deploy_config.limit)
    log.ok("Period", deploy_config.period)
    log.ok("Spent amount", deploy_config.spent_amount)
    log.ok("Trusted caller", deploy_config.trusted_caller)
    log.ok("Titles", deploy_config.titles)
    log.ok("Recipients", deploy_config.recipients)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    tx = allowed_recipients_builder.deployFullSetup(
        deploy_config.trusted_caller,
        deploy_config.token,
        deploy_config.limit,
        deploy_config.period,
        deploy_config.recipients,
        deploy_config.titles,
        deploy_config.spent_amount,
        tx_params,
    )

    allowed_recipients_registry_address = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    top_up_allowed_recipients_address = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
    add_allowed_recipient_address = tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
    remove_allowed_recipient_address = tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]

    log.ok("Allowed recipients easy track contracts have been deployed...")
    log.nb("Deployed AllowedRecipientsRegistry", allowed_recipients_registry_address)
    log.nb("Deployed AddAllowedRecipient", add_allowed_recipient_address)
    log.nb("Deployed RemoveAllowedRecipient", remove_allowed_recipient_address)
    log.nb("Deployed TopUpAllowedRecipients", top_up_allowed_recipients_address)

    log.br()

    log.nb("Running acceptance test...")

    run_acceptance_test(deploy_config, tx.txid)
