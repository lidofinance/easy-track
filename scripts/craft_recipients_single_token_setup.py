from brownie import chain, network

from utils import log, lido, deployment
from utils.config import get_is_live, get_deployer_account, prompt_bool


deploy_config = deployment.AllowedRecipientsManualSetupDeployConfig(
    token="",
    limit=0,
    period=1,
    spent_amount=0,
    trusted_caller="",
    titles=[],
    recipients=[],
    grant_rights_to_executor=False,
)


def main():
    network_name = network.show_active()
    deployer = get_deployer_account(get_is_live(), network=network_name)
    allowed_recipients_builder = lido.allowed_recipients_builder(network=network_name)

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
    log.ok(
        "Grant manager rights to EVMScriptExecutor",
        deploy_config.grant_rights_to_executor,
    )

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    tx = allowed_recipients_builder.deployAllowedRecipientsRegistry(
        deploy_config.limit,
        deploy_config.period,
        deploy_config.recipients,
        deploy_config.titles,
        deploy_config.spent_amount,
        deploy_config.grant_rights_to_executor,
        tx_params,
    )

    allowed_recipients_registry_address = tx.events[
        "AllowedRecipientsRegistryDeployed"
    ]["allowedRecipientsRegistry"]

    log.ok(
        f"AllowedRecipientsRegistry was deployed on address {allowed_recipients_registry_address}\n"
    )

    tx = allowed_recipients_builder.deployTopUpAllowedRecipients(
        deploy_config.trusted_caller,
        allowed_recipients_registry_address,
        deploy_config.token,
        tx_params,
    )

    top_up_allowed_recipients_address = tx.events["TopUpAllowedRecipientsDeployed"][
        "topUpAllowedRecipients"
    ]

    log.ok(
        f"TopUpAllowedRecipients EVM script factory was deployed on address {top_up_allowed_recipients_address}\n"
    )
