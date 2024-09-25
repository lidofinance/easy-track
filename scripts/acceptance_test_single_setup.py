from brownie import (
    chain,
    network,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AllowedTokensRegistry,
)

from utils.config import (
    get_network_name,
)
from utils.test_helpers import (
    ADD_TOKEN_TO_ALLOWED_LIST_ROLE,
    REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE,
    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
    SET_PARAMETERS_ROLE,
    UPDATE_SPENT_AMOUNT_ROLE,
    DEFAULT_ADMIN_ROLE,
)
from utils import lido, deployed_easy_track, log, deployment
from hexbytes import HexBytes

GRANT_ROLE_EVENT = "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d"
REVOKE_ROLE_EVENT = "0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b"


deploy_config = deployment.AllowedRecipientsSingleRecipientSetupDeployConfig(
    period=1,
    spent_amount=0,
    title="",
    limit=0,
    tokens=[],
    trusted_caller="",
)

deployment_tx_hash = ""
recipients_registry_deploy_tx_hash = ""
tokens_registry_deploy_tx_hash = ""
top_up_allowed_recipients_deploy_tx_hash = ""


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

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    recipients_registry_address = recipients_registry_deploy_tx.events[
        "AllowedRecipientsRegistryDeployed"
    ]["allowedRecipientsRegistry"]
    tokens_registry_address = tokens_registry_deploy_tx.events[
        "AllowedTokensRegistryDeployed"
    ]["allowedTokensRegistry"]
    top_up_allowed_recipient_address = top_up_deploy_tx.events[
        "TopUpAllowedRecipientsDeployed"
    ]["topUpAllowedRecipients"]
    log.br()

    log.nb("tx of creation", deployment_tx_hash)

    log.br()

    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("tokens", deploy_config.tokens)
    log.nb("limit", deploy_config.limit)
    log.nb("title", deploy_config.title)
    log.nb("period", deploy_config.period)
    log.nb("spent_amount", deploy_config.spent_amount)

    log.br()

    log.nb("AllowedRecipientsRegistryDeployed", recipients_registry_address)
    log.nb("AllowedTokensRegistryDeployed", tokens_registry_address)
    log.nb("TopUpAllowedRecipientsDeployed", top_up_allowed_recipient_address)

    log.br()

    recipients_registry = AllowedRecipientsRegistry.at(recipients_registry_address)
    top_up_allowed_recipients = TopUpAllowedRecipients.at(
        top_up_allowed_recipient_address
    )
    tokens_registry = AllowedTokensRegistry.at(tokens_registry_address)

    assert top_up_allowed_recipients.allowedRecipientsRegistry() == recipients_registry
    assert top_up_allowed_recipients.trustedCaller() == deploy_config.trusted_caller

    assert len(recipients_registry.getAllowedRecipients()) == 1
    assert recipients_registry.isRecipientAllowed(deploy_config.trusted_caller)

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

    assert not recipients_registry.hasRole(
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor
    )
    assert not recipients_registry.hasRole(
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

    assert tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)
    assert tokens_registry.hasRole(
        ADD_TOKEN_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent
    )
    assert tokens_registry.hasRole(
        REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent
    )

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
        "ADD_TOKEN_TO_ALLOWED_LIST_ROLE role holders",
        registry_roles_holders[ADD_TOKEN_TO_ALLOWED_LIST_ROLE],
    )
    log.nb(
        "REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE role holders",
        registry_roles_holders[REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE],
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
