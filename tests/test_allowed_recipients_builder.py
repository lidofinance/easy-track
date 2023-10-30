import pytest
from brownie import Contract, reverts
from utils.test_helpers import (
    ADD_TOKEN_TO_ALLOWED_LIST_ROLE,
    REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE,
)

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
DEFAULT_ADMIN_ROLE = "0x00"


@pytest.fixture(scope="module")
def allowed_recipients_factory(owner, AllowedRecipientsFactory):
    return owner.deploy(
        AllowedRecipientsFactory,
    )


@pytest.fixture(scope="module")
def allowed_recipients_builder(
    owner,
    AllowedRecipientsBuilder,
    allowed_recipients_factory,
    agent,
    finance,
    easy_track,
    bokkyPooBahsDateTimeContract,
):
    return owner.deploy(
        AllowedRecipientsBuilder,
        allowed_recipients_factory,
        agent,
        easy_track,
        finance,
        bokkyPooBahsDateTimeContract,
    )


def test_builder_constructor_params(
    allowed_recipients_factory,
    easy_track,
    evm_script_executor,
    agent,
    finance,
    bokkyPooBahsDateTimeContract,
    allowed_recipients_builder,
):
    assert allowed_recipients_builder.factory() == allowed_recipients_factory
    assert allowed_recipients_builder.admin() == agent
    assert allowed_recipients_builder.finance() == finance
    assert allowed_recipients_builder.easyTrack() == easy_track
    assert (
        allowed_recipients_builder.bokkyPooBahsDateTimeContract()
        == bokkyPooBahsDateTimeContract
    )
    assert allowed_recipients_builder.evmScriptExecutor() == evm_script_executor


def test_deploy_top_up_allowed_recipients(
    allowed_recipients_builder,
    accounts,
    stranger,
    finance,
    easy_track,
    TopUpAllowedRecipients,
):
    trusted_caller = accounts[3]
    recipients_registry = accounts[4]
    tokens_registry = accounts[4]

    tx = allowed_recipients_builder.deployTopUpAllowedRecipients(
        trusted_caller, recipients_registry, tokens_registry, {"from": stranger}
    )

    top_up_address = tx.events["TopUpAllowedRecipientsDeployed"][
        "topUpAllowedRecipients"
    ]

    assert (
        tx.events["TopUpAllowedRecipientsDeployed"]["creator"]
        == allowed_recipients_builder
    )
    assert (
        tx.events["TopUpAllowedRecipientsDeployed"]["trustedCaller"] == trusted_caller
    )
    assert (
        tx.events["TopUpAllowedRecipientsDeployed"]["allowedRecipientsRegistry"]
        == recipients_registry
    )
    assert tx.events["TopUpAllowedRecipientsDeployed"]["finance"] == finance
    assert tx.events["TopUpAllowedRecipientsDeployed"]["easyTrack"] == easy_track

    topUpAllowedRecipients = Contract.from_abi(
        "TopUpAllowedRecipients", top_up_address, TopUpAllowedRecipients.abi
    )
    assert topUpAllowedRecipients.allowedRecipientsRegistry() == recipients_registry
    assert topUpAllowedRecipients.allowedTokensRegistry() == tokens_registry
    assert topUpAllowedRecipients.trustedCaller() == trusted_caller
    assert topUpAllowedRecipients.finance() == finance
    assert topUpAllowedRecipients.easyTrack() == easy_track


def test_deploy_add_allowed_recipient(
    allowed_recipients_builder, accounts, stranger, AddAllowedRecipient
):
    trusted_caller = accounts[3]
    registry = accounts[4]

    tx = allowed_recipients_builder.deployAddAllowedRecipient(
        trusted_caller, registry, {"from": stranger}
    )

    add_recipient_address = tx.events["AddAllowedRecipientDeployed"][
        "addAllowedRecipient"
    ]

    assert (
        tx.events["AddAllowedRecipientDeployed"]["creator"]
        == allowed_recipients_builder
    )
    assert tx.events["AddAllowedRecipientDeployed"]["trustedCaller"] == trusted_caller
    assert (
        tx.events["AddAllowedRecipientDeployed"]["allowedRecipientsRegistry"]
        == registry
    )

    addAllowedRecipient = Contract.from_abi(
        "AddAllowedRecipient", add_recipient_address, AddAllowedRecipient.abi
    )

    assert addAllowedRecipient.allowedRecipientsRegistry() == registry
    assert addAllowedRecipient.trustedCaller() == trusted_caller


def test_deploy_remove_allowed_recipient(
    allowed_recipients_builder, accounts, stranger, RemoveAllowedRecipient
):
    trusted_caller = accounts[3]
    registry = accounts[4]

    tx = allowed_recipients_builder.deployRemoveAllowedRecipient(
        trusted_caller, registry, {"from": stranger}
    )

    remove_allowed_recipient_address = tx.events["RemoveAllowedRecipientDeployed"][
        "removeAllowedRecipient"
    ]

    assert (
        tx.events["RemoveAllowedRecipientDeployed"]["creator"]
        == allowed_recipients_builder
    )
    assert (
        tx.events["RemoveAllowedRecipientDeployed"]["trustedCaller"] == trusted_caller
    )
    assert (
        tx.events["RemoveAllowedRecipientDeployed"]["allowedRecipientsRegistry"]
        == registry
    )

    removeAllowedRecipient = Contract.from_abi(
        "RemoveAllowedRecipient",
        remove_allowed_recipient_address,
        RemoveAllowedRecipient.abi,
    )

    assert removeAllowedRecipient.allowedRecipientsRegistry() == registry
    assert removeAllowedRecipient.trustedCaller() == trusted_caller


def test_deploy_allowed_recipients_registry(
    allowed_recipients_builder,
    accounts,
    stranger,
    agent,
    evm_script_executor,
    AllowedRecipientsRegistry,
):
    limit = 1e18
    period = 1
    recipients = [accounts[3], accounts[4]]
    titles = ["account 3", "account 4"]
    spentAmount = 1e10

    tx_recipients = allowed_recipients_builder.deployAllowedRecipientsRegistry(
        limit, period, recipients, titles, spentAmount, True, {"from": stranger}
    )

    recipient_registry_address = tx_recipients.events[
        "AllowedRecipientsRegistryDeployed"
    ]["allowedRecipientsRegistry"]

    recipient_registry = Contract.from_abi(
        "AllowedRecipientsRegistry",
        recipient_registry_address,
        AllowedRecipientsRegistry.abi,
    )

    assert len(recipient_registry.getAllowedRecipients()) == len(recipients)
    for recipient in recipients:
        assert recipient_registry.isRecipientAllowed(recipient)

    registry_limit, registry_period_duration = recipient_registry.getLimitParameters()
    assert registry_limit == limit
    assert registry_period_duration == period

    assert recipient_registry.spendableBalance() == limit - spentAmount

    assert recipient_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, agent)
    assert recipient_registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, agent)
    assert recipient_registry.hasRole(SET_PARAMETERS_ROLE, agent)
    assert recipient_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, agent)
    assert recipient_registry.hasRole(DEFAULT_ADMIN_ROLE, agent)

    assert recipient_registry.hasRole(
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor
    )
    assert recipient_registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor
    )
    assert recipient_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not recipient_registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not recipient_registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    assert not recipient_registry.hasRole(
        ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, recipient_registry_address
    )
    assert not recipient_registry.hasRole(
        REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, recipient_registry_address
    )
    assert not recipient_registry.hasRole(
        SET_PARAMETERS_ROLE, recipient_registry_address
    )
    assert not recipient_registry.hasRole(
        UPDATE_SPENT_AMOUNT_ROLE, recipient_registry_address
    )
    assert not recipient_registry.hasRole(
        DEFAULT_ADMIN_ROLE, recipient_registry_address
    )


def test_deploy_allowed_tokens_registry(
    allowed_recipients_builder,
    AllowedTokensRegistry,
    stranger,
    agent,
    ldo,
    usdc,
):
    tx_tokens = allowed_recipients_builder.deployAllowedTokensRegistry(
        [ldo, usdc], {"from": stranger}
    )
    token_registry_address = tx_tokens.events["AllowedTokensRegistryDeployed"][
        "allowedTokensRegistry"
    ]
    token_registry = Contract.from_abi(
        "AllowedTokensRegistry", token_registry_address, AllowedTokensRegistry.abi
    )

    assert token_registry.isTokenAllowed(ldo)
    assert token_registry.isTokenAllowed(usdc)
    assert token_registry.getAllowedTokens() == [ldo, usdc]
    assert len(token_registry.getAllowedTokens()) == 2

    assert token_registry.hasRole(DEFAULT_ADMIN_ROLE, agent)
    assert not token_registry.hasRole(DEFAULT_ADMIN_ROLE, token_registry_address)
    assert not token_registry.hasRole(DEFAULT_ADMIN_ROLE, allowed_recipients_builder)

    assert token_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, agent)
    assert token_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, agent)

    assert not token_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, token_registry_address)
    assert not token_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, token_registry_address)
    assert not token_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, allowed_recipients_builder)
    assert not token_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, allowed_recipients_builder)


def test_deploy_recipients_registry_reverts_recipients_length(
    allowed_recipients_builder, accounts, stranger, ldo
):
    limit = 1e18
    period = 1
    recipients = [accounts[3], accounts[4]]
    titles = ["account 3"]
    spentAmount = 1e10

    with reverts():
        allowed_recipients_builder.deployAllowedRecipientsRegistry(
            limit, period, recipients, titles, spentAmount, False, {"from": stranger}
        )


def test_deploy_recipients_registry_reverts_spentAmount_gt_limit(
    allowed_recipients_builder, accounts, stranger, ldo
):
    limit = 1e5
    period = 1
    tokens = [ldo]
    recipients = [accounts[3], accounts[4]]
    titles = ["account 3", "account 4"]
    spentAmount = 1e10

    with reverts("_spentAmount must be lower or equal to limit"):
        allowed_recipients_builder.deployAllowedRecipientsRegistry(
            limit, period, recipients, titles, spentAmount, False, {"from": stranger}
        )


def test_deploy_full_setup(
    allowed_recipients_builder,
    stranger,
    agent,
    ldo,
    evm_script_executor,
    AllowedRecipientsRegistry,
    AllowedTokensRegistry,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
    TopUpAllowedRecipients,
):
    recipients = [
        "0xbbe8dDEf5BF31b71Ff5DbE89635f9dB4DeFC667E",
        "0x07fC01f46dC1348d7Ce43787b5Bbd52d8711a92D",
        "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1",
        "0xDDFFac49946D1F6CE4d9CaF3B9C7d340d4848A1C",
        "0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97",
    ]
    titles = [
        "Default Reward Program",
        "Happy",
        "Sergey'2 #add RewardProgram",
        "Jumpgate Test",
        "tester",
    ]
    trusted_caller = "0x3eaE0B337413407FB3C65324735D797ddc7E071D"
    limit = 10_000 * 1e18
    period = 1
    spent_amount = 0

    tx = allowed_recipients_builder.deployFullSetup(
        trusted_caller,
        limit,
        period,
        [ldo],
        recipients,
        titles,
        spent_amount,
        {"from": stranger},
    )

    recipients_registry_address = tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]
    tokens_registry_address = tx.events["AllowedTokensRegistryDeployed"][
        "allowedTokensRegistry"
    ]
    top_up_address = tx.events["TopUpAllowedRecipientsDeployed"][
        "topUpAllowedRecipients"
    ]
    add_recipient_address = tx.events["AddAllowedRecipientDeployed"][
        "addAllowedRecipient"
    ]
    remove_allowed_recipient_address = tx.events["RemoveAllowedRecipientDeployed"][
        "removeAllowedRecipient"
    ]

    recipients_registry = Contract.from_abi(
        "AllowedRecipientsRegistry",
        recipients_registry_address,
        AllowedRecipientsRegistry.abi,
    )

    tokens_registry = Contract.from_abi(
        "AllowedTokensRegistry", tokens_registry_address, AllowedTokensRegistry.abi
    )

    top_up_allowed_recipients = Contract.from_abi(
        "TopUpAllowedRecipients", top_up_address, TopUpAllowedRecipients.abi
    )

    add_allowed_recipient = Contract.from_abi(
        "AddAllowedRecipient", add_recipient_address, AddAllowedRecipient.abi
    )

    remove_allowed_recipient = Contract.from_abi(
        "RemoveAllowedRecipient",
        remove_allowed_recipient_address,
        RemoveAllowedRecipient.abi,
    )

    assert top_up_allowed_recipients.allowedRecipientsRegistry() == recipients_registry
    assert top_up_allowed_recipients.trustedCaller() == trusted_caller
    assert add_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert add_allowed_recipient.trustedCaller() == trusted_caller
    assert remove_allowed_recipient.allowedRecipientsRegistry() == recipients_registry
    assert remove_allowed_recipient.trustedCaller() == trusted_caller

    assert len(recipients_registry.getAllowedRecipients()) == len(recipients)
    for recipient in recipients:
        assert recipients_registry.isRecipientAllowed(recipient)

    registry_limit, registry_period_duration = recipients_registry.getLimitParameters()
    assert registry_limit == limit
    assert registry_period_duration == period

    assert recipients_registry.spendableBalance() == limit - spent_amount

    assert recipients_registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, agent)
    assert recipients_registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, agent)
    assert recipients_registry.hasRole(SET_PARAMETERS_ROLE, agent)
    assert recipients_registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, agent)
    assert recipients_registry.hasRole(DEFAULT_ADMIN_ROLE, agent)

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

    assert tokens_registry.isTokenAllowed(ldo)
    assert tokens_registry.getAllowedTokens() == [ldo]
    assert len(tokens_registry.getAllowedTokens()) == 1

    assert tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, agent)
    assert not tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, tokens_registry_address)

    assert tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, agent)
    assert tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, agent)

    assert not tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, tokens_registry_address)
    assert not tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, tokens_registry_address)
    assert not tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, allowed_recipients_builder)
    assert not tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, allowed_recipients_builder)


def test_deploy_deploy_single_recipient_top_up_only_setup(
    allowed_recipients_builder,
    accounts,
    agent,
    ldo,
    stranger,
    evm_script_executor,
    AllowedRecipientsRegistry,
    AllowedTokensRegistry,
    TopUpAllowedRecipients,
):
    recipient = accounts[2]
    title = "recipient"
    limit = 1e18
    period = 1
    spent_amount = 1e10

    tx = allowed_recipients_builder.deploySingleRecipientTopUpOnlySetup(
        recipient, title, [ldo], limit, period, spent_amount, {"from": stranger}
    )

    registry_address = tx.events["AllowedRecipientsRegistryDeployed"][
        "allowedRecipientsRegistry"
    ]
    tokens_registry_address = tx.events["AllowedTokensRegistryDeployed"][
        "allowedTokensRegistry"
    ]
    top_up_address = tx.events["TopUpAllowedRecipientsDeployed"][
        "topUpAllowedRecipients"
    ]

    registry = Contract.from_abi(
        "AllowedRecipientsRegistry", registry_address, AllowedRecipientsRegistry.abi
    )
    tokens_registry = Contract.from_abi(
        "AllowedTokensRegistry", tokens_registry_address, AllowedTokensRegistry.abi
    )

    top_up_allowed_recipients = Contract.from_abi(
        "TopUpAllowedRecipients", top_up_address, TopUpAllowedRecipients.abi
    )

    assert top_up_allowed_recipients.allowedRecipientsRegistry() == registry

    assert len(registry.getAllowedRecipients()) == 1
    assert registry.isRecipientAllowed(recipient)

    registry_limit, registry_period_duration = registry.getLimitParameters()
    assert registry_limit == limit
    assert registry_period_duration == period

    assert registry.spendableBalance() == limit - spent_amount

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, agent)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, agent)
    assert registry.hasRole(SET_PARAMETERS_ROLE, agent)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, agent)
    assert registry.hasRole(DEFAULT_ADMIN_ROLE, agent)

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

    assert tokens_registry.isTokenAllowed(ldo)
    assert tokens_registry.getAllowedTokens() == [ldo]
    assert len(tokens_registry.getAllowedTokens()) == 1

    assert tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, agent)
    assert not tokens_registry.hasRole(DEFAULT_ADMIN_ROLE, tokens_registry_address)

    assert tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, agent)
    assert tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, agent)

    assert not tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, tokens_registry_address)
    assert not tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, tokens_registry_address)
    assert not tokens_registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, allowed_recipients_builder)
    assert not tokens_registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, allowed_recipients_builder)
