from hexbytes import HexBytes
from brownie import chain, network, AllowedRecipientsRegistry, TopUpAllowedRecipients

from utils import lido, deployed_easy_track, log, deployment

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

registry_deploy_tx_hash = ""
top_up_deploy_tx_hash = ""


def main():
    network_name = network.show_active()

    if network_name is None:
        raise Exception("network_name is None")

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    registry_deploy_tx = chain.get_transaction(registry_deploy_tx_hash)
    registry_address = registry_deploy_tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]

    top_up_deploy_tx = chain.get_transaction(top_up_deploy_tx_hash)
    top_up_address = top_up_deploy_tx.events["TopUpAllowedRecipientsDeployed"][
        "topUpAllowedRecipients"
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
    log.nb("grant_rights_to_executor", deploy_config.grant_rights_to_executor)

    log.br()

    log.nb("AllowedRecipientsRegistryDeployed", registry_address)
    log.nb("TopUpAllowedRecipientsDeployed", top_up_address)

    log.br()

    registry = AllowedRecipientsRegistry.at(registry_address)
    top_up_allowed_recipients = TopUpAllowedRecipients.at(top_up_address)

    assert top_up_allowed_recipients.token() == deploy_config.token
    assert top_up_allowed_recipients.allowedRecipientsRegistry() == registry
    assert top_up_allowed_recipients.trustedCaller() == deploy_config.trusted_caller

    assert len(registry.getAllowedRecipients()) == len(deploy_config.recipients)
    for recipient in deploy_config.recipients:
        assert registry.isRecipientAllowed(recipient)

    registryLimit, registryPeriodDuration = registry.getLimitParameters()
    assert registryLimit == deploy_config.limit
    assert registryPeriodDuration == deploy_config.period

    assert (
        registry.spendableBalance() == deploy_config.limit - deploy_config.spent_amount
    )

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent
    )
    assert registry.hasRole(SET_PARAMETERS_ROLE, contracts.aragon.agent)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, contracts.aragon.agent)
    assert registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)

    if deploy_config.grant_rights_to_executor:
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

    if registry_deploy_tx.logs is None:
        raise Exception("Can't validate logs. The logs is None.")

    for event in registry_deploy_tx.logs or []:
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
