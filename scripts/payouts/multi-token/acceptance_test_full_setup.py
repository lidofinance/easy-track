from brownie import (
    chain,
    network,
    AllowedTokensRegistry,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
)

from utils import lido, deployed_easy_track, log, deployment
from hexbytes import HexBytes

from utils.test_helpers import (
    ADD_TOKEN_TO_ALLOWED_LIST_ROLE,
    REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE,
    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
    SET_PARAMETERS_ROLE,
    UPDATE_SPENT_AMOUNT_ROLE,
    DEFAULT_ADMIN_ROLE,
)

GRANT_ROLE_EVENT = "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d"
REVOKE_ROLE_EVENT = "0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b"

deploy_config = deployment.AllowedRecipientsMultiTokenFullSetupDeployConfig(
    tokens=["", ""],  # the list of tokens in which transfers can be made,  ex. ["0x2EB8E9198e647f80CCF62a5E291BCD4a5a3cA68c", "0x86F6c353A0965eB069cD7f4f91C1aFEf8C725551", "0x9715b2786F1053294FC8952dF923b95caB9Aac42"],
    tokens_registry="",  # a token registry that includes a list of tokens in which transfers can be made, ex. "0x091c0ec8b4d54a9fcb36269b5d5e5af43309e666"
    limit=0,  # budget amount, ex. 1_000_000 * 10 ** 18,
    period=1,  # budget period duration in month, ex. 3
    spent_amount=0, # budget already spent, ex. 0
    titles=["", ""], # allowed recipients titles, ex. ["LEGO LDO funder", "LEGO Stables funder"]
    recipients=["", ""], # allowed recipients addresses, ex. ["0x96d2Ff1C4D30f592B91fd731E218247689a76915", "0x1580881349e214Bab9f1E533bF97351271DB95a9"]
    trusted_caller="", # multisig / trusted caller's address, ex. "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
    grant_rights = False, # permissions to execute AddAllowedRecipient / RemoveAllowedRecipient methods on behalf of trusted_caller
)

deployment_tx_hash = ""

recipients_registry_deploy_tx_hash = ""
tokens_registry_deploy_tx_hash = ""
top_up_allowed_recipients_deploy_tx_hash = ""
add_allowed_token_deploy_tx_hash = ""
remove_allowed_token_deploy_tx_hash = ""


def main():
    network_name = network.show_active()

    recipients_registry_deploy_tx = chain.get_transaction(
        recipients_registry_deploy_tx_hash or deployment_tx_hash
    )
    tokens_registry_deploy_tx = chain.get_transaction(
        tokens_registry_deploy_tx_hash or deployment_tx_hash
    )
    top_up_deploy_tx = chain.get_transaction(
        top_up_allowed_recipients_deploy_tx_hash or deployment_tx_hash
    )
    add_allowed_token_deploy_tx = chain.get_transaction(
        add_allowed_token_deploy_tx_hash or deployment_tx_hash
    )
    remove_allowed_recipient_deploy_tx = chain.get_transaction(
        remove_allowed_token_deploy_tx_hash or deployment_tx_hash
    )

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    recipients_registry_address = recipients_registry_deploy_tx.events[
        "AllowedRecipientsRegistryDeployed"
    ]["allowedRecipientsRegistry"]
    tokens_registry_address = tokens_registry_deploy_tx.events[
        "AllowedTokensRegistryDeployed"
    ]["allowedTokensRegistry"]
    top_up_address = top_up_deploy_tx.events[
        "TopUpAllowedRecipientsDeployed"
    ]["topUpAllowedRecipients"]
    add_allowed_recipient_address = add_allowed_token_deploy_tx.events[
        "AddAllowedRecipientDeployed"
    ]["addAllowedRecipient"]
    remove_allowed_recipient_address = remove_allowed_recipient_deploy_tx.events[
        "RemoveAllowedRecipientDeployed"
    ]["removeAllowedRecipient"]

    log.br()

    log.nb("Agent", contracts.aragon.agent)
    log.nb("Easy Track EVM Script Executor", evm_script_executor)

    log.br()

    log.nb("recipients", deploy_config.recipients)
    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("limit", deploy_config.limit)
    log.nb("period", deploy_config.period)
    log.nb("spent_amount", deploy_config.spent_amount)

    log.br()

    log.nb("AllowedRecipientsRegistryDeployed", recipients_registry_address)
    log.nb("TopUpAllowedRecipientsDeployed", top_up_address)
    log.nb("AddAllowedRecipientDeployed", add_allowed_recipient_address)
    log.nb("RemoveAllowedRecipientDeployed", remove_allowed_recipient_address)

    log.br()

    recipients_registry = AllowedRecipientsRegistry.at(recipients_registry_address)
    tokens_registry = AllowedTokensRegistry.at(tokens_registry_address)
    top_up_allowed_recipients = TopUpAllowedRecipients.at(top_up_address)
    add_allowed_recipient = AddAllowedRecipient.at(add_allowed_recipient_address)
    remove_allowed_recipient = RemoveAllowedRecipient.at(
        remove_allowed_recipient_address
    )

    assert tokens_registry.getAllowedTokens() == deploy_config.tokens
    assert len(tokens_registry.getAllowedTokens()) == len(deploy_config.tokens)

    assert top_up_allowed_recipients.allowedRecipientsRegistry() == recipients_registry
    assert top_up_allowed_recipients.trustedCaller() == deploy_config.trusted_caller
    assert add_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert add_allowed_recipient.trustedCaller() == deploy_config.trusted_caller
    assert remove_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert remove_allowed_recipient.trustedCaller() == deploy_config.trusted_caller

    assert len(recipients_registry.getAllowedRecipients()) == len(
        deploy_config.recipients
    )
    for recipient in deploy_config.recipients:
        assert recipients_registry.isRecipientAllowed(recipient)

    registryLimit, registryPeriodDuration = recipients_registry.getLimitParameters()
    assert registryLimit == deploy_config.limit
    assert registryPeriodDuration == deploy_config.period

    assert (
        recipients_registry.spendableBalance()
        == deploy_config.limit - deploy_config.spent_amount
    )

    assert recipients_registry.hasRole(
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent
    )
    assert recipients_registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent
    )
    assert recipients_registry.hasRole(SET_PARAMETERS_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)

    if deploy_config.grant_rights:
        assert recipients_registry.hasRole(
            ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor
        )
        assert recipients_registry.hasRole(
            REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor
        )

    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not recipients_registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    assert not recipients_registry.hasRole(
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, recipients_registry_address
    )
    assert not recipients_registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, recipients_registry_address
    )
    assert not recipients_registry.hasRole(
        SET_PARAMETERS_ROLE, recipients_registry_address
    )
    assert not recipients_registry.hasRole(
        UPDATE_SPENT_AMOUNT_ROLE, recipients_registry_address
    )
    assert not recipients_registry.hasRole(
        DEFAULT_ADMIN_ROLE, recipients_registry_address
    )

    for token in deploy_config.tokens:
        assert tokens_registry.isTokenAllowed(token)

    assert tokens_registry.getAllowedTokens() == deploy_config.tokens
    assert len(tokens_registry.getAllowedTokens()) == len(deploy_config.tokens)

    assert tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.voting)

    assert not tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, tokens_registry_address)
    assert not tokens_registry.hasRole(
        ADD_TOKEN_TO_ALLOWED_LIST_ROLE, tokens_registry_address
    )
    assert not tokens_registry.hasRole(
        REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, tokens_registry_address
    )

    registry_roles_holders = {
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE: [],
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE: [],
        SET_PARAMETERS_ROLE: [],
        UPDATE_SPENT_AMOUNT_ROLE: [],
        DEFAULT_ADMIN_ROLE: [],
        ADD_TOKEN_TO_ALLOWED_LIST_ROLE: [],
        REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE: [],
    }

    def log_to_key(log):
        return log["address"]

    all_logs = (
        recipients_registry_deploy_tx.logs
        + tokens_registry_deploy_tx.logs
        + top_up_deploy_tx.logs
        + add_allowed_token_deploy_tx.logs
        + remove_allowed_recipient_deploy_tx.logs
    )

    unique_logs = []
    seen_keys = set()

    for l in all_logs:
        key = log_to_key(l)
        if key not in seen_keys:
            unique_logs.append(l)
            seen_keys.add(key)

    for event in all_logs:
        if event["topics"][0] == HexBytes(GRANT_ROLE_EVENT):
            registry_roles_holders[event["topics"][1].hex()].append(
                "0x" + event["topics"][2].hex()[26:]
            )
        elif event["topics"][0] == HexBytes(REVOKE_ROLE_EVENT):
            registry_roles_holders[event["topics"][1].hex()].remove(
                "0x" + event["topics"][2].hex()[26:]
            )

    log.br()

    log.nb("Roles holders from tx events")

    log.br()

    log.nb(
        "ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE role holders",
        registry_roles_holders[ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE],
    )
    log.nb(
        "REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE role holders",
        registry_roles_holders[REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE],
    )
    log.nb(
        "SET_PARAMETERS_ROLE role holders",
        registry_roles_holders[SET_PARAMETERS_ROLE],
    )
    log.nb(
        "UPDATE_SPENT_AMOUNT_ROLE role holders",
        registry_roles_holders[UPDATE_SPENT_AMOUNT_ROLE],
    )
    log.nb(
        "DEFAULT_ADMIN_ROLE role holders",
        registry_roles_holders[DEFAULT_ADMIN_ROLE],
    )

    log.br()