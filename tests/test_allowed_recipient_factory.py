import pytest
from brownie import Contract

ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = "0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276"
REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE = "0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b"
SET_LIMIT_PARAMETERS_ROLE = "0x389c107d46e44659ea9e3d38a2e43f5414bdd0fd8244fa558561536ea90c2ece"
UPDATE_SPENT_AMOUNT_ROLE = "0xc5260260446719a726d11a6faece21d19daa48b4cbcca118345832d4cb71df99"
DEFAULT_ADMIN_ROLE = "0x00"

@pytest.fixture(scope="module")
def allowed_recipients_factory(
    owner,
    entire_allowed_recipients_setup,
    agent,
    finance,
    bokkyPooBahsDateTimeContract,
    AllowedRecipientsFactory
):
    return owner.deploy(
        AllowedRecipientsFactory,
        entire_allowed_recipients_setup.easy_track,
        finance,
        entire_allowed_recipients_setup.evm_script_executor,
        agent,
        bokkyPooBahsDateTimeContract
    )


@pytest.fixture(scope="module")
def allowed_recipients_builder(
    owner,
    AllowedRecipientsBuilder,
    allowed_recipients_factory,
    entire_allowed_recipients_setup,
    agent,
):
    return owner.deploy(
        AllowedRecipientsBuilder,
        allowed_recipients_factory,
        entire_allowed_recipients_setup.evm_script_executor,
        agent
    )


def test_delploy_topup(
    allowed_recipients_builder, 
    accounts,
    stranger, 
    ldo,
    finance,
    entire_allowed_recipients_setup,
    TopUpAllowedRecipients
):
    trustedCaller = accounts[3];
    registry = accounts[4];

    tx = allowed_recipients_builder.deployTopUpAllowedRecipients(
        trustedCaller,
        registry,
        ldo,
        {"from": stranger}
    )
    
    topUpAddress = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
    
    assert tx.events["TopUpAllowedRecipientsDeployed"]["creator"] == allowed_recipients_builder
    assert tx.events["TopUpAllowedRecipientsDeployed"]["trustedCaller"] == trustedCaller
    assert tx.events["TopUpAllowedRecipientsDeployed"]["allowedRecipientsRegistry"] == registry
    assert tx.events["TopUpAllowedRecipientsDeployed"]["finance"] == finance
    assert tx.events["TopUpAllowedRecipientsDeployed"]["token"] == ldo
    assert tx.events["TopUpAllowedRecipientsDeployed"]["easyTrack"] == entire_allowed_recipients_setup.easy_track

    topUpAllowedRecipients = Contract.from_abi(
        "TopUpAllowedRecipients", 
        topUpAddress,
        TopUpAllowedRecipients.abi
    )
    assert topUpAllowedRecipients.token() == ldo
    assert topUpAllowedRecipients.allowedRecipientsRegistry() == registry


def test_delploy_add_recipient(
    allowed_recipients_builder, 
    accounts,
    stranger,
    AddAllowedRecipient
):
    trustedCaller = accounts[3];
    registry = accounts[4];

    tx = allowed_recipients_builder.deployAddAllowedRecipient(
        trustedCaller,
        registry,
        {"from": stranger}
    )
    
    addRecipientAddress = tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
    
    assert tx.events["AddAllowedRecipientDeployed"]["creator"] == allowed_recipients_builder
    assert tx.events["AddAllowedRecipientDeployed"]["trustedCaller"] == trustedCaller
    assert tx.events["AddAllowedRecipientDeployed"]["allowedRecipientsRegistry"] == registry

    addAllowedRecipient = Contract.from_abi(
        "AddAllowedRecipient", 
        addRecipientAddress,
        AddAllowedRecipient.abi
    )

    assert addAllowedRecipient.allowedRecipientsRegistry() == registry


def test_delploy_remove_recipient(
    allowed_recipients_builder, 
    accounts,
    stranger,
    AddAllowedRecipient
):
    trustedCaller = accounts[3];
    registry = accounts[4];

    tx = allowed_recipients_builder.deployRemoveAllowedRecipient(
        trustedCaller,
        registry,
        {"from": stranger}
    )
    
    addRecipientAddress = tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]

    assert tx.events["RemoveAllowedRecipientDeployed"]["creator"] == allowed_recipients_builder
    assert tx.events["RemoveAllowedRecipientDeployed"]["trustedCaller"] == trustedCaller
    assert tx.events["RemoveAllowedRecipientDeployed"]["allowedRecipientsRegistry"] == registry

    addAllowedRecipient = Contract.from_abi(
        "AddAllowedRecipient", 
        addRecipientAddress,
        AddAllowedRecipient.abi
    )

    assert addAllowedRecipient.allowedRecipientsRegistry() == registry


def test_delploy_recipients_registry(
    allowed_recipients_builder, 
    accounts,
    stranger, 
    agent,
    entire_allowed_recipients_setup,
    AllowedRecipientsRegistry
):
    limit = 1e18
    period = 1
    recipients = [accounts[3], accounts[4]]
    titles = ["account 3", "account 4"]
    spentAmount = 1e10

    tx = allowed_recipients_builder.deployAllowedRecipientsRegistry(
        limit,
        period,
        recipients,
        titles,
        spentAmount,
        {"from": stranger}
    )
    
    regestryAddress = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]

    registry = Contract.from_abi(
        "AllowedRecipientsRegistry", 
        regestryAddress,
        AllowedRecipientsRegistry.abi
    )

    assert len(registry.getAllowedRecipients()) == len(recipients)
    for recipient in recipients:
        assert registry.isRecipientAllowed(recipient)
    
    registryLimit, registryPeriodDuration = registry.getLimitParameters()
    assert registryLimit == limit
    assert registryPeriodDuration == period

    assert registry.spendableBalance() == limit - spentAmount
    
    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, agent)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, agent)
    assert registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, agent)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, agent)
    assert registry.hasRole(DEFAULT_ADMIN_ROLE, agent)

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, entire_allowed_recipients_setup.evm_script_executor)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, entire_allowed_recipients_setup.evm_script_executor)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, entire_allowed_recipients_setup.evm_script_executor)
    assert not registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, entire_allowed_recipients_setup.evm_script_executor)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, entire_allowed_recipients_setup.evm_script_executor)

    assert not registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, regestryAddress)
    assert not registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, regestryAddress)
    assert not registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, regestryAddress)
    assert not registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, regestryAddress)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, regestryAddress)