from brownie import (
    chain,
    network,
    AllowedTokensRegistry,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
)

from utils.config import (
    get_network_name,
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
    DEFAULT_ADMIN_ROLE
)

GRANT_ROLE_EVENT = "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d"
REVOKE_ROLE_EVENT = "0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b"

deploy_config = deployment.AllowedRecipientsFullSetupDeployConfig(
    tokens=["0xD87Ba7A50B2E7E660f678A895E4B72E7CB4CCd9C", "0x56340274fB5a72af1A3C6609061c451De7961Bd4"],
    limit=10000000000000000000, 
    period=1,
    spent_amount=0,
    trusted_caller="0x4333218072d5d7008546737786663c38b4d561a4",  
    titles=["Agent"],
    recipients=["0x4333218072d5d7008546737786663c38b4d561a4"],
)

deployment_tx_hash = "0x8fb7b98a7acdca0028fb8439278feff4ded27609c390274cc7b3ec0142b76133"


def main():
    network_name = network.show_active()

    tx = chain.get_transaction(deployment_tx_hash)

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    recipients_registry_address = tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]
    tokens_registry_address = tx.events["AllowedTokensRegistryDeployed"][
        "allowedTokensRegistry"
    ]
    top_up_address = tx.events["TopUpAllowedRecipientsDeployed"][
        "topUpAllowedRecipients"
    ]
    add_allowed_recipient_address = tx.events["AddAllowedRecipientDeployed"][
        "addAllowedRecipient"
    ]
    remove_allowed_recipient_address = tx.events["RemoveAllowedRecipientDeployed"][
        "removeAllowedRecipient"
    ]

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

    assert len(recipients_registry.getAllowedRecipients()) == len(deploy_config.recipients)
    for recipient in deploy_config.recipients:
        assert recipients_registry.isRecipientAllowed(recipient)

    registryLimit, registryPeriodDuration = recipients_registry.getLimitParameters()
    assert registryLimit == deploy_config.limit
    assert registryPeriodDuration == deploy_config.period

    assert (
        recipients_registry.spendableBalance() == deploy_config.limit - deploy_config.spent_amount
    )

    assert recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent
    )
    assert recipients_registry.hasRole(SET_PARAMETERS_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)

    assert recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
    assert recipients_registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor
    )
    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not recipients_registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    assert not recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, recipients_registry_address)
    assert not recipients_registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, recipients_registry_address
    )
    assert not recipients_registry.hasRole(SET_PARAMETERS_ROLE, recipients_registry_address)
    assert not recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, recipients_registry_address)
    assert not recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, recipients_registry_address)

    registry_roles_holders = {
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE: [],
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE: [],
        SET_PARAMETERS_ROLE: [],
        UPDATE_SPENT_AMOUNT_ROLE: [],
        DEFAULT_ADMIN_ROLE: [],
        ADD_TOKEN_TO_ALLOWED_LIST_ROLE: [],
        REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE: [],
    }

    for event in tx.logs:
        # print(event["topics"][0])
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
