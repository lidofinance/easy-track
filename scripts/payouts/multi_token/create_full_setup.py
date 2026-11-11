from dataclasses import dataclass

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
from scripts.payouts.multi_token.acceptance_test_full_setup import main as run_acceptance_test

"""

Please fill out deploy_config before running the script.

A. If you want a new token registry to be created when the script is executed:
- fill in the "tokens" parameter in the deploy_config with a list of tokens to be added to the registry
- leave the "tokens_registry" parameter empty

    Example:
    tokens=["0x2EB8E9198e647f80CCF62a5E291BCD4a5a3cA68c", "0x86F6c353A0965eB069cD7f4f91C1aFEf8C725551"],
    tokens_registry = "",

B. If you prefer to use an existing token registry when the script is executed:
- fill in the "tokens_registry" parameter in the deploy_config with the address of the token registry that should be used
- fill in the "tokens" parameter with a list of tokens that are included in the specified registry - this will be used later during testing
- fill in "tokens_registry_deploy_tx_hash" with the hash of the transaction that deployed the registry - the acceptance test reads it

    Example:
    tokens=["0x2EB8E9198e647f80CCF62a5E291BCD4a5a3cA68c", "0x86F6c353A0965eB069cD7f4f91C1aFEf8C725551", "0x9715b2786F1053294FC8952dF923b95caB9Aac42"],
    tokens_registry = "0x091c0ec8b4d54a9fcb36269b5d5e5af43309e666",

The "tokens_registry" parameter of the deploy_config is used primarily to verify the method of contracts deployment.
Please make sure you have filled deploy_config correctly.

"grant_rights" is honored in both cases. With grant_rights=False the AddAllowedRecipient and RemoveAllowedRecipient
factories are still deployed, but the EVMScriptExecutor cannot enact their motions until the DAO grants
ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE and REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE to it on the recipients registry,
normally in the vote that registers the factories in Easy Track.

"""

deploy_config = deployment.AllowedRecipientsMultiTokenFullSetupDeployConfig(
    tokens=[],  # the list of tokens in which transfers can be made,  ex. ["0x2EB8E9198e647f80CCF62a5E291BCD4a5a3cA68c", "0x86F6c353A0965eB069cD7f4f91C1aFEf8C725551", "0x9715b2786F1053294FC8952dF923b95caB9Aac42"],
    tokens_registry="",  # a token registry that includes a list of tokens in which transfers can be made, ex. "0x091c0ec8b4d54a9fcb36269b5d5e5af43309e666"
    limit=0,  # budget amount, ex. 1_000_000 * 10 ** 18,
    period=1,  # budget period duration in month, ex. 3
    spent_amount=0,  # budget already spent, ex. 0
    titles=[],  # allowed recipients titles, ex. ["LEGO LDO funder", "LEGO Stables funder"]
    recipients=[],  # allowed recipients addresses, ex. ["0x96d2Ff1C4D30f592B91fd731E218247689a76915", "0x1580881349e214Bab9f1E533bF97351271DB95a9"]
    trusted_caller="",  # multisig / trusted caller's address, ex. "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
    grant_rights=False,  # permissions to execute AddAllowedRecipient / RemoveAllowedRecipient methods on behalf of trusted_caller
)
tokens_registry_deploy_tx_hash = ""  # If tokens_registry is not empty, this tx hash should be specified


@dataclass
class MultiTokenFullSetupDeployment:
    allowed_recipients_registry: str
    allowed_tokens_registry: str
    top_up_allowed_recipients: str
    add_allowed_recipient: str
    remove_allowed_recipient: str
    allowed_recipients_registry_tx_hash: str
    allowed_tokens_registry_tx_hash: str
    top_up_allowed_recipients_tx_hash: str
    add_allowed_recipient_tx_hash: str
    remove_allowed_recipient_tx_hash: str


def main():

    if deploy_config.tokens and deploy_config.tokens_registry:
        new_token_registry_is_required = False
    elif deploy_config.tokens and not deploy_config.tokens_registry:
        new_token_registry_is_required = True
    elif not deploy_config.tokens and deploy_config.tokens_registry:
        log.nb("The deploy_config filled in incorrectly.")
        log.nb("Please, specify in the deploy_config the list of tokens that are included in the registry.")
        log.nb("Aborting...")
        return
    else:
        log.nb("The deploy_config filled in incorrectly.")
        log.nb(
            "Please specify the tokens parameter and optionally specify the tokens_registry parameter in the deploy_config."
        )
        log.nb("Aborting...")
        return

    if not new_token_registry_is_required and not tokens_registry_deploy_tx_hash:
        log.nb("The deploy_config filled in incorrectly.")
        log.nb("Please specify tokens_registry_deploy_tx_hash for the existing tokens_registry.")
        log.nb("Aborting...")
        return

    network_name = network.show_active()
    deployer = get_deployer_account(get_is_live(), network=network_name)
    allowed_recipients_builder = lido.allowed_recipients_builder_multi_token(network=network_name)

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("Chain id", chain.id)
    log.ok("Deployer", deployer)
    log.br()

    if new_token_registry_is_required:
        log.nb("During the deployment, a new token registry will be created.")
        log.ok("Tokens", deploy_config.tokens)
    else:
        log.nb("During the deployment, the existing token registry will be used.")
        log.ok("Tokens registry", deploy_config.tokens_registry)

    log.ok("Limit", deploy_config.limit)
    log.ok("Period", deploy_config.period)
    log.ok("Spent amount", deploy_config.spent_amount)
    log.ok("Titles", deploy_config.titles)
    log.ok("Recipients", deploy_config.recipients)
    log.ok("Trusted caller", deploy_config.trusted_caller)
    log.ok("Grant add/remove recipient rights to EVMScriptExecutor", deploy_config.grant_rights)
    if not deploy_config.grant_rights:
        log.warning(
            "AddAllowedRecipient and RemoveAllowedRecipient will be deployed but cannot enact motions until "
            "ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE and REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE are granted to the "
            "EVMScriptExecutor on the recipients registry, normally by the DAO vote that registers the factories"
        )
    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting...")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    deployed = deploy_full_setup(allowed_recipients_builder, deploy_config, tx_params, tokens_registry_deploy_tx_hash)

    log.ok("Allowed recipients Easy Track contracts have been deployed!")
    log.nb("Deployed AllowedRecipientsRegistry", deployed.allowed_recipients_registry)
    log.nb(
        "Deployed AllowedTokensRegistry" if new_token_registry_is_required else "Used AllowedTokensRegistry",
        deployed.allowed_tokens_registry,
    )
    log.nb("Deployed AddAllowedRecipient", deployed.add_allowed_recipient)
    log.nb("Deployed RemoveAllowedRecipient", deployed.remove_allowed_recipient)
    log.nb("Deployed TopUpAllowedRecipients", deployed.top_up_allowed_recipients)

    log.br()

    log.nb("Running acceptance test...")

    run_acceptance_test(
        deploy_config,
        deployed.allowed_recipients_registry_tx_hash,
        deployed.allowed_tokens_registry_tx_hash,
        deployed.top_up_allowed_recipients_tx_hash,
        deployed.add_allowed_recipient_tx_hash,
        deployed.remove_allowed_recipient_tx_hash,
    )


def deploy_full_setup(allowed_recipients_builder, deploy_config, tx_params, tokens_registry_deploy_tx_hash=""):
    """Deploys the multi-token allowed recipients setup contract by contract so that grant_rights is always honored.

    The builder's deployFullSetup is not used: it hard-codes granting the add/remove recipient roles to the executor.
    The recipients registry goes first: it is the only call with config checks, so a bad config reverts before
    anything is deployed."""
    recipients_registry_tx = allowed_recipients_builder.deployAllowedRecipientsRegistry(
        deploy_config.limit,
        deploy_config.period,
        deploy_config.recipients,
        deploy_config.titles,
        deploy_config.spent_amount,
        deploy_config.grant_rights,
        tx_params,
    )
    allowed_recipients_registry = recipients_registry_tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]

    if deploy_config.tokens_registry:
        allowed_tokens_registry = deploy_config.tokens_registry
    else:
        tokens_registry_tx = allowed_recipients_builder.deployAllowedTokensRegistry(deploy_config.tokens, tx_params)
        allowed_tokens_registry = tokens_registry_tx.events["AllowedTokensRegistryDeployed"]["allowedTokensRegistry"]
        tokens_registry_deploy_tx_hash = tokens_registry_tx.txid

    top_up_tx = allowed_recipients_builder.deployTopUpAllowedRecipients(
        deploy_config.trusted_caller, allowed_recipients_registry, allowed_tokens_registry, tx_params
    )
    add_recipient_tx = allowed_recipients_builder.deployAddAllowedRecipient(
        deploy_config.trusted_caller, allowed_recipients_registry, tx_params
    )
    remove_recipient_tx = allowed_recipients_builder.deployRemoveAllowedRecipient(
        deploy_config.trusted_caller, allowed_recipients_registry, tx_params
    )

    return MultiTokenFullSetupDeployment(
        allowed_recipients_registry=allowed_recipients_registry,
        allowed_tokens_registry=allowed_tokens_registry,
        top_up_allowed_recipients=top_up_tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"],
        add_allowed_recipient=add_recipient_tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"],
        remove_allowed_recipient=remove_recipient_tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"],
        allowed_recipients_registry_tx_hash=recipients_registry_tx.txid,
        allowed_tokens_registry_tx_hash=tokens_registry_deploy_tx_hash,
        top_up_allowed_recipients_tx_hash=top_up_tx.txid,
        add_allowed_recipient_tx_hash=add_recipient_tx.txid,
        remove_allowed_recipient_tx_hash=remove_recipient_tx.txid,
    )
