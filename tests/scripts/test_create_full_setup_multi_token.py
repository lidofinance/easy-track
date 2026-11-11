import brownie
import pytest
from scripts.payouts.multi_token.acceptance_test_full_setup import main as run_acceptance_test
from scripts.payouts.multi_token.create_full_setup import deploy_full_setup
from utils import deployed_easy_track, deployment, lido
from utils.test_helpers import (
    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
    UPDATE_SPENT_AMOUNT_ROLE,
)


def allowed_recipients_builder():
    return lido.allowed_recipients_builder_multi_token(network=brownie.network.show_active())


def live_evm_script_executor():
    return deployed_easy_track.contracts(network=brownie.network.show_active()).easy_track.evmScriptExecutor()


def full_setup_config(accounts, dai, usdc, grant_rights, tokens_registry=""):
    return deployment.AllowedRecipientsMultiTokenFullSetupDeployConfig(
        tokens=[dai, usdc],
        tokens_registry=tokens_registry,
        limit=100 * 10**18,
        period=1,
        spent_amount=0,
        titles=["Recipient A", "Recipient B"],
        recipients=[accounts[2].address, accounts[3].address],
        trusted_caller=accounts[1].address,
        grant_rights=grant_rights,
    )


def run_acceptance_test_for(deploy_config, deployed):
    run_acceptance_test(
        deploy_config,
        deployed.allowed_recipients_registry_tx_hash,
        deployed.allowed_tokens_registry_tx_hash,
        deployed.top_up_allowed_recipients_tx_hash,
        deployed.add_allowed_recipient_tx_hash,
        deployed.remove_allowed_recipient_tx_hash,
    )


@pytest.mark.parametrize("grant_rights", [True, False])
def test_deploy_full_setup_honors_grant_rights(
    accounts,
    dai,
    usdc,
    grant_rights,
    AllowedRecipientsRegistry,
    AllowedTokensRegistry,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
):
    deploy_config = full_setup_config(accounts, dai, usdc, grant_rights)
    deployed = deploy_full_setup(allowed_recipients_builder(), deploy_config, {"from": accounts[0]})

    recipients_registry = AllowedRecipientsRegistry.at(deployed.allowed_recipients_registry)
    evm_script_executor = live_evm_script_executor()
    assert recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor) == grant_rights
    assert recipients_registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor) == grant_rights
    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)

    # the factories are deployed regardless of grant_rights; the DAO empowers the executor later
    add_allowed_recipient = AddAllowedRecipient.at(deployed.add_allowed_recipient)
    assert add_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert add_allowed_recipient.trustedCaller() == deploy_config.trusted_caller
    remove_allowed_recipient = RemoveAllowedRecipient.at(deployed.remove_allowed_recipient)
    assert remove_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert remove_allowed_recipient.trustedCaller() == deploy_config.trusted_caller

    assert AllowedTokensRegistry.at(deployed.allowed_tokens_registry).getAllowedTokens() == [dai, usdc]

    run_acceptance_test_for(deploy_config, deployed)


def test_deploy_full_setup_with_existing_tokens_registry(accounts, dai, usdc, TopUpAllowedRecipients):
    builder = allowed_recipients_builder()
    tokens_registry_tx = builder.deployAllowedTokensRegistry([dai, usdc], {"from": accounts[0]})
    tokens_registry = tokens_registry_tx.events["AllowedTokensRegistryDeployed"]["allowedTokensRegistry"]
    deploy_config = full_setup_config(accounts, dai, usdc, grant_rights=False, tokens_registry=tokens_registry)

    deployed = deploy_full_setup(builder, deploy_config, {"from": accounts[0]}, tokens_registry_tx.txid)

    assert deployed.allowed_tokens_registry == tokens_registry
    assert deployed.allowed_tokens_registry_tx_hash == tokens_registry_tx.txid
    assert TopUpAllowedRecipients.at(deployed.top_up_allowed_recipients).allowedTokensRegistry() == tokens_registry

    run_acceptance_test_for(deploy_config, deployed)
