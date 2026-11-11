from brownie import (
    chain,
    network,
    AllowedTokensRegistry,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
)

from brownie.convert import to_address
from utils import lido, deployed_easy_track, log, deployment
from hexbytes import HexBytes

from utils.test_helpers import (
    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
    SET_PARAMETERS_ROLE,
    UPDATE_SPENT_AMOUNT_ROLE,
    DEFAULT_ADMIN_ROLE,
)

GRANT_ROLE_EVENT = "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d"
REVOKE_ROLE_EVENT = "0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b"

deploy_config = deployment.AllowedRecipientsMultiTokenFullSetupDeployConfig(
    tokens=[
        "",
        "",
    ],  # the list of tokens in which transfers can be made,  ex. ["0x2EB8E9198e647f80CCF62a5E291BCD4a5a3cA68c", "0x86F6c353A0965eB069cD7f4f91C1aFEf8C725551", "0x9715b2786F1053294FC8952dF923b95caB9Aac42"],
    tokens_registry="",  # a token registry that includes a list of tokens in which transfers can be made, ex. "0x091c0ec8b4d54a9fcb36269b5d5e5af43309e666"
    limit=0,  # budget amount, ex. 1_000_000 * 10 ** 18,
    period=1,  # budget period duration in month, ex. 3
    spent_amount=0,  # budget already spent, ex. 0
    titles=["", ""],  # allowed recipients titles, ex. ["LEGO LDO funder", "LEGO Stables funder"]
    recipients=[
        "",
        "",
    ],  # allowed recipients addresses, ex. ["0x96d2Ff1C4D30f592B91fd731E218247689a76915", "0x1580881349e214Bab9f1E533bF97351271DB95a9"]
    trusted_caller="",  # multisig / trusted caller's address, ex. "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
    grant_rights=False,  # permissions to execute AddAllowedRecipient / RemoveAllowedRecipient methods on behalf of trusted_caller
)

recipients_registry_deploy_tx_hash = ""
tokens_registry_deploy_tx_hash = ""
top_up_allowed_recipients_deploy_tx_hash = ""
add_allowed_recipient_deploy_tx_hash = ""
remove_allowed_recipient_deploy_tx_hash = ""


def main(
    deploy_config: deployment.AllowedRecipientsMultiTokenFullSetupDeployConfig,
    recipients_registry_deploy_tx_hash: str,
    tokens_registry_deploy_tx_hash: str,
    top_up_allowed_recipients_deploy_tx_hash: str,
    add_allowed_recipient_deploy_tx_hash: str,
    remove_allowed_recipient_deploy_tx_hash: str,
):
    network_name = network.show_active()

    recipients_registry_deploy_tx = chain.get_transaction(recipients_registry_deploy_tx_hash)
    tokens_registry_deploy_tx = chain.get_transaction(tokens_registry_deploy_tx_hash)
    top_up_deploy_tx = chain.get_transaction(top_up_allowed_recipients_deploy_tx_hash)
    add_allowed_recipient_deploy_tx = chain.get_transaction(add_allowed_recipient_deploy_tx_hash)
    remove_allowed_recipient_deploy_tx = chain.get_transaction(remove_allowed_recipient_deploy_tx_hash)

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    # the executor the registry must trust is the one Easy Track uses now, not a possibly stale address table entry
    evm_script_executor = et_contracts.easy_track.evmScriptExecutor()
    assert evm_script_executor == et_contracts.evm_script_executor

    recipients_registry_address = recipients_registry_deploy_tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]
    tokens_registry_address = tokens_registry_deploy_tx.events["AllowedTokensRegistryDeployed"]["allowedTokensRegistry"]
    top_up_address = top_up_deploy_tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
    add_allowed_recipient_address = add_allowed_recipient_deploy_tx.events["AddAllowedRecipientDeployed"][
        "addAllowedRecipient"
    ]
    remove_allowed_recipient_address = remove_allowed_recipient_deploy_tx.events["RemoveAllowedRecipientDeployed"][
        "removeAllowedRecipient"
    ]

    log.br()

    log.nb("Agent", contracts.aragon.agent)
    log.nb("Easy Track EVM Script Executor", evm_script_executor)

    log.br()

    log.nb("recipients", deploy_config.recipients)
    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("limit", deploy_config.limit)
    log.nb("titles", deploy_config.titles)
    log.nb("period", deploy_config.period)
    log.nb("spent_amount", deploy_config.spent_amount)

    log.br()

    log.nb("AllowedRecipientsRegistryDeployed", recipients_registry_address)
    log.nb("TopUpAllowedRecipientsDeployed", top_up_address)
    log.nb("AddAllowedRecipientDeployed", add_allowed_recipient_address)
    log.nb("RemoveAllowedRecipientDeployed", remove_allowed_recipient_address)
    log.nb("AllowedTokensRegistryDeployed", tokens_registry_address)

    log.br()

    recipients_registry = AllowedRecipientsRegistry.at(recipients_registry_address)
    tokens_registry = AllowedTokensRegistry.at(tokens_registry_address)
    top_up_allowed_recipients = TopUpAllowedRecipients.at(top_up_address)
    add_allowed_recipient = AddAllowedRecipient.at(add_allowed_recipient_address)
    remove_allowed_recipient = RemoveAllowedRecipient.at(remove_allowed_recipient_address)

    #####################
    # TopUpAllowedRecipients checks
    #####################

    assert top_up_allowed_recipients.allowedRecipientsRegistry() == recipients_registry
    assert top_up_allowed_recipients.allowedTokensRegistry() == tokens_registry
    assert top_up_allowed_recipients.trustedCaller() == deploy_config.trusted_caller
    assert top_up_allowed_recipients.finance() == contracts.aragon.finance
    assert top_up_allowed_recipients.easyTrack() == et_contracts.easy_track

    #####################
    # AddAllowedRecipient checks
    #####################

    assert add_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert add_allowed_recipient.trustedCaller() == deploy_config.trusted_caller

    #####################
    # RemoveAllowedRecipient checks
    #####################

    assert remove_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert remove_allowed_recipient.trustedCaller() == deploy_config.trusted_caller

    #####################
    # RecipientsRegistry checks
    #####################

    assert len(recipients_registry.getAllowedRecipients()) == len(deploy_config.recipients)
    for recipient in deploy_config.recipients:
        assert recipients_registry.isRecipientAllowed(recipient)

    registryLimit, registryPeriodDuration = recipients_registry.getLimitParameters()
    assert registryLimit == deploy_config.limit
    assert registryPeriodDuration == deploy_config.period

    assert recipients_registry.spendableBalance() == deploy_config.limit - deploy_config.spent_amount

    assert recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(SET_PARAMETERS_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, contracts.aragon.agent)
    assert recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)

    if deploy_config.grant_rights:
        assert recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
        assert recipients_registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor)
    else:
        assert not recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
        assert not recipients_registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor)

    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not recipients_registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    #####################
    # TokensRegistry checks
    #####################

    assert tokens_registry.getAllowedTokens() == deploy_config.tokens
    assert len(tokens_registry.getAllowedTokens()) == len(deploy_config.tokens)

    for token in deploy_config.tokens:
        assert tokens_registry.isTokenAllowed(token)

    assert tokens_registry.getAllowedTokens() == deploy_config.tokens
    assert len(tokens_registry.getAllowedTokens()) == len(deploy_config.tokens)

    is_admin_role_on_agent = tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)
    is_admin_role_on_voting = tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.voting)

    assert is_admin_role_on_agent or is_admin_role_on_voting

    if is_admin_role_on_agent:
        log.warning("DEFAULT_ADMIN_ROLE is on agent - after DG release this role should be on voting")

    #####################
    # Roles checks
    #####################

    # Replay RoleGranted / RoleRevoked emitted by the recipients registry across all deployment txs.
    # The builder's temporary grants are renounced within the same tx, so the replay nets out to the final holders.
    registry_roles = {
        "ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE": ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
        "REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE": REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
        "SET_PARAMETERS_ROLE": SET_PARAMETERS_ROLE,
        "UPDATE_SPENT_AMOUNT_ROLE": UPDATE_SPENT_AMOUNT_ROLE,
        "DEFAULT_ADMIN_ROLE": DEFAULT_ADMIN_ROLE,
    }
    role_topic_names = {HexBytes(role): name for name, role in registry_roles.items()}
    registry_roles_holders = {name: set() for name in registry_roles}

    all_logs = (
        recipients_registry_deploy_tx.logs
        + tokens_registry_deploy_tx.logs
        + top_up_deploy_tx.logs
        + add_allowed_recipient_deploy_tx.logs
        + remove_allowed_recipient_deploy_tx.logs
    )

    for event in all_logs:
        if to_address(event["address"]) != recipients_registry.address:
            continue
        if event["topics"][0] == HexBytes(GRANT_ROLE_EVENT):
            role_name = role_topic_names[event["topics"][1]]
            registry_roles_holders[role_name].add(to_address(event["topics"][2][-20:]))
        elif event["topics"][0] == HexBytes(REVOKE_ROLE_EVENT):
            role_name = role_topic_names[event["topics"][1]]
            registry_roles_holders[role_name].remove(to_address(event["topics"][2][-20:]))

    log.br()

    log.nb("Roles holders from tx events")

    log.br()

    for role_name, holders in registry_roles_holders.items():
        log.nb(f"{role_name} role holders", sorted(holders))

    log.br()

    agent = to_address(contracts.aragon.agent.address)
    executor = to_address(evm_script_executor)
    add_remove_recipient_holders = {agent, executor} if deploy_config.grant_rights else {agent}
    assert registry_roles_holders == {
        "ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE": add_remove_recipient_holders,
        "REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE": add_remove_recipient_holders,
        "SET_PARAMETERS_ROLE": {agent},
        "UPDATE_SPENT_AMOUNT_ROLE": {agent, executor},
        "DEFAULT_ADMIN_ROLE": {agent},
    }
    log.ok("Recipients registry role holders match the expected layout")
