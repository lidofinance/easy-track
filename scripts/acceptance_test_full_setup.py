from brownie import (
    chain,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
)

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

    recipients = [
        "0xbbe8dDEf5BF31b71Ff5DbE89635f9dB4DeFC667E",
        "0x07fC01f46dC1348d7Ce43787b5Bbd52d8711a92D",
        "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1",
        "0xDDFFac49946D1F6CE4d9CaF3B9C7d340d4848A1C",
        "0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97",
    ]
    trusted_caller = "0x3eaE0B337413407FB3C65324735D797ddc7E071D"
    limit = 10_000 * 1e18
    period = 1
    spent_amount = 0

    tx = chain.get_transaction(
        "0xd8bfe8b817231afb4851ac5926a84feb69b0a204f6ac37c3f3b91c6b8180981d"
    )

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    registry_address = tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
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
    log.nb("LDO Token", contracts.ldo)
    log.nb("Easy Track EVM Script Executor", evm_script_executor)

    log.br()

    log.nb("recipients", recipients)
    log.nb("trusted_caller", trusted_caller)
    log.nb("limit", limit)
    log.nb("period", period)
    log.nb("spent_amount", spent_amount)

    log.br()

    log.nb("AllowedRecipientsRegistryDeployed", registry_address)
    log.nb("TopUpAllowedRecipientsDeployed", top_up_address)
    log.nb("AddAllowedRecipientDeployed", add_allowed_recipient_address)
    log.nb("RemoveAllowedRecipientDeployed", remove_allowed_recipient_address)

    log.br()

    registry = AllowedRecipientsRegistry.at(registry_address)
    top_up_allowed_recipients = TopUpAllowedRecipients.at(top_up_address)
    add_allowed_recipient = AddAllowedRecipient.at(add_allowed_recipient_address)
    remove_allowed_recipient = RemoveAllowedRecipient.at(
        remove_allowed_recipient_address
    )

    assert top_up_allowed_recipients.token() == contracts.ldo
    assert top_up_allowed_recipients.allowedRecipientsRegistry() == registry
    assert top_up_allowed_recipients.trustedCaller() == trusted_caller
    assert add_allowed_recipient.allowedRecipientsRegistry() == registry
    assert add_allowed_recipient.trustedCaller() == trusted_caller
    assert remove_allowed_recipient.allowedRecipientsRegistry() == registry
    assert remove_allowed_recipient.trustedCaller() == trusted_caller

    assert len(registry.getAllowedRecipients()) == len(recipients)
    for recipient in recipients:
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

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
    assert registry.hasRole(
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
