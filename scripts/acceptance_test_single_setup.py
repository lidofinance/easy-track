from brownie import chain, AllowedRecipientsRegistry, TopUpAllowedRecipients

from utils.config import (
    get_network_name,
)
from utils import lido, deployed_easy_track, log
from hexbytes import HexBytes

ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = (
    "0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276"
)
REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE = (
    "0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b"
)
SET_PARAMETERS_ROLE = (
    "0x260b83d52a26066d8e9db550fa70395df5f3f064b50ff9d8a94267d9f1fe1967"
)
UPDATE_SPENT_AMOUNT_ROLE = (
    "0xc5260260446719a726d11a6faece21d19daa48b4cbcca118345832d4cb71df99"
)
DEFAULT_ADMIN_ROLE = (
    "0x0000000000000000000000000000000000000000000000000000000000000000"
)

GRANT_ROLE_EVENT = "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d"
REVOKE_ROLE_EVENT = "0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b"


def main():
    network_name = get_network_name()

    recipient = "0x3eaE0B337413407FB3C65324735D797ddc7E071D"
    token = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    limit = 10_000 * 1e18
    period = 1
    spent_amount = 0

    tx_of_creation = (
        "0xcf663eebff6ce76b03867a2f32c6456b5bbb4a11e6441798fb15409c7ca39fab"
    )

    tx = chain.get_transaction(tx_of_creation)

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    registry_address = tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]
    add_allowed_recipient_address = tx.events["TopUpAllowedRecipientsDeployed"][
        "topUpAllowedRecipients"
    ]
    log.br()

    log.nb("tx of creation", tx_of_creation)

    log.br()

    log.nb("recipient", recipient)
    log.nb("token", token)
    log.nb("limit", limit)
    log.nb("period", period)
    log.nb("spent_amount", spent_amount)

    log.br()

    log.nb("AllowedRecipientsRegistryDeployed", registry_address)
    log.nb("TopUpAllowedRecipientsDeployed", add_allowed_recipient_address)

    log.br()

    registry = AllowedRecipientsRegistry.at(registry_address)
    top_up_allowed_recipients = TopUpAllowedRecipients.at(add_allowed_recipient_address)

    assert top_up_allowed_recipients.token() == token
    assert top_up_allowed_recipients.allowedRecipientsRegistry() == registry
    assert top_up_allowed_recipients.trustedCaller() == recipient

    assert len(registry.getAllowedRecipients()) == 1
    assert registry.isRecipientAllowed(recipient)

    registryLimit, registryPeriodDuration = registry.getLimitParameters()
    assert registryLimit == limit
    assert registryPeriodDuration == period

    assert registry.spendableBalance() == limit - spent_amount

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent
    )
    assert registry.hasRole(SET_PARAMETERS_ROLE, contracts.aragon.agent)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, contracts.aragon.agent)
    assert registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)

    assert not registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
    assert not registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor
    )
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    assert not registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, registry_address)
    assert not registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, registry_address
    )
    assert not registry.hasRole(SET_PARAMETERS_ROLE, registry_address)
    assert not registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, registry_address)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, registry_address)

    registry_roles_holders = {
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE: [],
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE: [],
        SET_PARAMETERS_ROLE: [],
        UPDATE_SPENT_AMOUNT_ROLE: [],
        DEFAULT_ADMIN_ROLE: [],
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
