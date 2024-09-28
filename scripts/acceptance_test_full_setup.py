from brownie import (
    chain,
    network,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
)

from utils import lido, deployed_easy_track, deployed_date_time, log, deployment
from hexbytes import HexBytes

ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = "0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276"
REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE = "0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b"
SET_PARAMETERS_ROLE = "0x260b83d52a26066d8e9db550fa70395df5f3f064b50ff9d8a94267d9f1fe1967"
UPDATE_SPENT_AMOUNT_ROLE = "0xc5260260446719a726d11a6faece21d19daa48b4cbcca118345832d4cb71df99"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"

GRANT_ROLE_EVENT = "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d"
REVOKE_ROLE_EVENT = "0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b"

deploy_config = deployment.AllowedRecipientsFullSetupDeployConfig(
    token="",
    limit=0,
    period=1,
    spent_amount=0,
    trusted_caller="",
    titles=[],
    recipients=[],
)

deployment_tx_hash = ""


def main():
    network_name = network.show_active()

    tx = chain.get_transaction(deployment_tx_hash)

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)
    date_time_contract = deployed_date_time.date_time_contract(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    registry_address = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    top_up_address = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
    add_allowed_recipient_address = tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
    remove_allowed_recipient_address = tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]

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

    log.nb("AllowedRecipientsRegistryDeployed", registry_address)
    log.nb("TopUpAllowedRecipientsDeployed", top_up_address)
    log.nb("AddAllowedRecipientDeployed", add_allowed_recipient_address)
    log.nb("RemoveAllowedRecipientDeployed", remove_allowed_recipient_address)

    log.br()

    registry = AllowedRecipientsRegistry.at(registry_address)
    top_up_allowed_recipients = TopUpAllowedRecipients.at(top_up_address)
    add_allowed_recipient = AddAllowedRecipient.at(add_allowed_recipient_address)
    remove_allowed_recipient = RemoveAllowedRecipient.at(remove_allowed_recipient_address)

    assert registry.bokkyPooBahsDateTimeContract() == date_time_contract
    assert top_up_allowed_recipients.easyTrack() == et_contracts.easy_track
    assert top_up_allowed_recipients.finance() == contracts.aragon.finance
    assert top_up_allowed_recipients.token() == deploy_config.token
    assert top_up_allowed_recipients.allowedRecipientsRegistry() == registry
    assert top_up_allowed_recipients.trustedCaller() == deploy_config.trusted_caller
    assert add_allowed_recipient.allowedRecipientsRegistry() == registry
    assert add_allowed_recipient.trustedCaller() == deploy_config.trusted_caller
    assert remove_allowed_recipient.allowedRecipientsRegistry() == registry
    assert remove_allowed_recipient.trustedCaller() == deploy_config.trusted_caller

    assert len(registry.getAllowedRecipients()) == len(deploy_config.recipients)
    for recipient in deploy_config.recipients:
        assert registry.isRecipientAllowed(recipient)

    registryLimit, registryPeriodDuration = registry.getLimitParameters()
    assert registryLimit == deploy_config.limit
    assert registryPeriodDuration == deploy_config.period

    assert registry.spendableBalance() == deploy_config.limit - deploy_config.spent_amount

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert registry.hasRole(SET_PARAMETERS_ROLE, contracts.aragon.agent)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, contracts.aragon.agent)
    assert registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    assert not registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, registry_address)
    assert not registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, registry_address)
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
            registry_roles_holders[event["topics"][1].hex()].append("0x" + event["topics"][2].hex()[26:])
        elif event["topics"][0] == HexBytes(REVOKE_ROLE_EVENT):
            registry_roles_holders[event["topics"][1].hex()].remove("0x" + event["topics"][2].hex()[26:])

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
