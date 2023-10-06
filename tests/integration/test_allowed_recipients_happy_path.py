import pytest
from dataclasses import dataclass
from brownie import (
    chain,
    reverts,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
)
from utils import deployment, evm_script, test_helpers

MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60


@dataclass
class SingleRecipientTopUpOnlySetup:
    allowed_recipients_registry: AllowedRecipientsRegistry
    top_up_allowed_recipients_ldo_evm_script_factory: TopUpAllowedRecipients
    top_up_allowed_recipients_usdc_evm_script_factory: TopUpAllowedRecipients


@dataclass
class FullSetup(SingleRecipientTopUpOnlySetup):
    add_allowed_recipient_evm_script_factory: AddAllowedRecipient
    remove_allowed_recipient_evm_script_factory: RemoveAllowedRecipient


@pytest.fixture(scope="module")
def allowed_recipient(recipients):
    return recipients[0]


@pytest.fixture(scope="module")
def new_recipient(recipients):
    return recipients[1]


@pytest.fixture(scope="module")
def single_recipient_top_up_only_setup(
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    easy_track,
    lido_contracts,
    external_contracts,
    allowed_recipient,
    allowed_recipients_builder,
    allowed_recipients_default_params,
    deployer,
):
    deploy_tx = allowed_recipients_builder.deploySingleRecipientTopUpOnlySetup(
        allowed_recipient.address,
        allowed_recipient.title,
        [lido_contracts.ldo, external_contracts["usdc"]],
        allowed_recipients_default_params.limit,
        allowed_recipients_default_params.period_duration_months,
        allowed_recipients_default_params.spent_amount,
        {"from": deployer},
    )

    allowed_recipients_registry = AllowedRecipientsRegistry.at(
        deploy_tx.events["AllowedRecipientsRegistryDeployed"][
            "allowedRecipientsRegistry"
        ]
    )
    top_up_allowed_recipients_ldo_evm_script_factory = TopUpAllowedRecipients.at(
        deploy_tx.events["TopUpAllowedRecipientsDeployed"][0]["topUpAllowedRecipients"]
    )
    top_up_allowed_recipients_usdc_evm_script_factory = TopUpAllowedRecipients.at(
        deploy_tx.events["TopUpAllowedRecipientsDeployed"][1]["topUpAllowedRecipients"]
    )

    easy_track.addEVMScriptFactory(
        top_up_allowed_recipients_ldo_evm_script_factory,
        deployment.create_permission(
            lido_contracts.aragon.finance, "newImmediatePayment"
        )
        + deployment.create_permission(
            allowed_recipients_registry, "updateSpentAmount"
        )[2:],
        {"from": lido_contracts.aragon.voting},
    )
    easy_track.addEVMScriptFactory(
        top_up_allowed_recipients_usdc_evm_script_factory,
        deployment.create_permission(
            lido_contracts.aragon.finance, "newImmediatePayment"
        )
        + deployment.create_permission(
            allowed_recipients_registry, "updateSpentAmount"
        )[2:],
        {"from": lido_contracts.aragon.voting},
    )
    return SingleRecipientTopUpOnlySetup(
        allowed_recipients_registry,
        top_up_allowed_recipients_ldo_evm_script_factory,
        top_up_allowed_recipients_usdc_evm_script_factory,
    )


@pytest.fixture(scope="module")
def full_setup(
    AllowedRecipientsRegistry,
    AddAllowedRecipient,
    TopUpAllowedRecipients,
    RemoveAllowedRecipient,
    easy_track,
    allowed_recipients_builder,
    trusted_caller,
    lido_contracts,
    allowed_recipients_default_params,
    deployer,
    ldo,
    usdc
):
    deploy_tx = allowed_recipients_builder.deployFullSetup(
        trusted_caller,
        allowed_recipients_default_params.limit,
        allowed_recipients_default_params.period_duration_months,
        [ldo, usdc],
        [],
        [],
        allowed_recipients_default_params.spent_amount,
        {"from": deployer},
    )

    allowed_recipients_registry = AllowedRecipientsRegistry.at(
        deploy_tx.events["AllowedRecipientsRegistryDeployed"][
            "allowedRecipientsRegistry"
        ]
    )

    add_allowed_recipient_evm_script_factory = AddAllowedRecipient.at(
        deploy_tx.events["AddAllowedRecipientDeployed"][0]["addAllowedRecipient"]
    )

    easy_track.addEVMScriptFactory(
        add_allowed_recipient_evm_script_factory,
        deployment.create_permission(allowed_recipients_registry, "addRecipient"),
        {"from": lido_contracts.aragon.voting},
    )

    remove_allowed_recipient_evm_script_factory = RemoveAllowedRecipient.at(
        deploy_tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]
    )
    easy_track.addEVMScriptFactory(
        remove_allowed_recipient_evm_script_factory,
        deployment.create_permission(allowed_recipients_registry, "removeRecipient"),
        {"from": lido_contracts.aragon.voting},
    )

    top_up_allowed_recipients_ldo_evm_script_factory = TopUpAllowedRecipients.at(
        deploy_tx.events["TopUpAllowedRecipientsDeployed"][0]["topUpAllowedRecipients"]
    )
    top_up_allowed_recipients_usdc_evm_script_factory = TopUpAllowedRecipients.at(
        deploy_tx.events["TopUpAllowedRecipientsDeployed"][1]["topUpAllowedRecipients"]
    )
    easy_track.addEVMScriptFactory(
        top_up_allowed_recipients_ldo_evm_script_factory,
        deployment.create_permission(
            lido_contracts.aragon.finance, "newImmediatePayment"
        )
        + deployment.create_permission(
            allowed_recipients_registry, "updateSpentAmount"
        )[2:],
        {"from": lido_contracts.aragon.voting},
    )
    easy_track.addEVMScriptFactory(
        top_up_allowed_recipients_usdc_evm_script_factory,
        deployment.create_permission(
            lido_contracts.aragon.finance, "newImmediatePayment"
        )
        + deployment.create_permission(
            allowed_recipients_registry, "updateSpentAmount"
        )[2:],
        {"from": lido_contracts.aragon.voting},
    )

    return FullSetup(
        allowed_recipients_registry,
        top_up_allowed_recipients_ldo_evm_script_factory,
        top_up_allowed_recipients_usdc_evm_script_factory,
        add_allowed_recipient_evm_script_factory,
        remove_allowed_recipient_evm_script_factory,
    )


def test_single_recipient_top_up_only_setup_happy_path(
    lido_contracts,
    evm_script_executor,
    allowed_recipients_default_params,
    single_recipient_top_up_only_setup,
    top_up_allowed_recipient_by_motion,
    allowed_recipient,
    new_recipient,
):
    first_top_up_amount = 100 * 10**6
    second_top_up_amount = 100 * 10**18

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_default_params.period_duration_months
    )

    allowed_recipients_registry = (
        single_recipient_top_up_only_setup.allowed_recipients_registry
    )
    top_up_allowed_recipients_ldo_evm_script_factory = (
        single_recipient_top_up_only_setup.top_up_allowed_recipients_ldo_evm_script_factory
    )
    top_up_allowed_recipients_usdc_evm_script_factory = (
        single_recipient_top_up_only_setup.top_up_allowed_recipients_usdc_evm_script_factory
    )

    # Top up allowed recipient

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_usdc_evm_script_factory,
        [allowed_recipient.address],
        [first_top_up_amount],
    )

    # Validate Aragon Agent can remove recipient
    assert allowed_recipients_registry.isRecipientAllowed(allowed_recipient.address)

    allowed_recipients_registry.removeRecipient(
        allowed_recipient.address, {"from": lido_contracts.aragon.agent}
    )

    assert not allowed_recipients_registry.isRecipientAllowed(allowed_recipient.address)

    # Validate EVM Script Executor can't add recipient
    with reverts(
        test_helpers.access_revert_message(
            evm_script_executor,
            allowed_recipients_registry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE(),
        )
    ):
        allowed_recipients_registry.addRecipient(
            new_recipient.address, new_recipient.title, {"from": evm_script_executor}
        )

    # Validate Aragon Agent can add recipient
    allowed_recipients_registry.addRecipient(
        new_recipient.address,
        new_recipient.title,
        {"from": lido_contracts.aragon.agent},
    )

    assert allowed_recipients_registry.isRecipientAllowed(new_recipient.address)

    # Validate EVM Script Executor can't remove recipient
    with reverts(
        test_helpers.access_revert_message(
            evm_script_executor,
            allowed_recipients_registry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE(),
        )
    ):
        allowed_recipients_registry.removeRecipient(
            new_recipient.address, {"from": evm_script_executor}
        )

    # wait next period

    chain.sleep(
        allowed_recipients_default_params.period_duration_months * MAX_SECONDS_IN_MONTH
    )

    # Top up newly added recipient

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_ldo_evm_script_factory,
        [new_recipient.address],
        [second_top_up_amount],
    )

    # Validate motion creation fails if the limit was exceeded
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(
            top_up_allowed_recipients_ldo_evm_script_factory,
            [new_recipient.address],
            [1],
        )


def test_full_setup_happy_path(
    full_setup,
    lido_contracts,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
    remove_allowed_recipient_by_motion,
    allowed_recipients_default_params,
    allowed_recipient,
    new_recipient,
):
    first_top_up_amount = 50 * 10**6
    second_top_up_amount = 100 * 10**18

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_default_params.period_duration_months
    )

    # Add allowed recipient by motion
    add_allowed_recipient_evm_script_factory = (
        full_setup.add_allowed_recipient_evm_script_factory
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipient.address,
        allowed_recipient.title,
    )

    # Top up allowed recipient by motion
    top_up_allowed_recipients_ldo_evm_script_factory = (
        full_setup.top_up_allowed_recipients_ldo_evm_script_factory
    )
    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_ldo_evm_script_factory,
        [allowed_recipient.address],
        [first_top_up_amount],
    )

    # Remove allowed recipient by motion
    remove_allowed_recipient_evm_script_factory = (
        full_setup.remove_allowed_recipient_evm_script_factory
    )
    remove_allowed_recipient_by_motion(
        remove_allowed_recipient_evm_script_factory, allowed_recipient.address
    )

    # Aragon's Agent can add new recipients
    allowed_recipients_registry = full_setup.allowed_recipients_registry

    assert not allowed_recipients_registry.isRecipientAllowed(new_recipient.address)
    allowed_recipients_registry.addRecipient(
        new_recipient.address,
        new_recipient.title,
        {"from": lido_contracts.aragon.agent},
    )
    assert allowed_recipients_registry.isRecipientAllowed(new_recipient.address)

    # Wait for next period
    chain.sleep(
        allowed_recipients_default_params.period_duration_months * MAX_SECONDS_IN_MONTH
    )

    # Top up newly allowed recipient by motion
    top_up_allowed_recipients_ldo_evm_script_factory = (
        full_setup.top_up_allowed_recipients_ldo_evm_script_factory
    )
    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_ldo_evm_script_factory,
        [new_recipient.address],
        [second_top_up_amount],
    )

    # Validate motion creation cause limit was spent
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(
            top_up_allowed_recipients_ldo_evm_script_factory,
            [new_recipient.address],
            [1],
        )

    # Aragon's Agent can remove recipients
    allowed_recipients_registry = full_setup.allowed_recipients_registry

    assert allowed_recipients_registry.isRecipientAllowed(new_recipient.address)
    allowed_recipients_registry.removeRecipient(
        new_recipient.address,
        {"from": lido_contracts.aragon.agent},
    )
    assert not allowed_recipients_registry.isRecipientAllowed(new_recipient.address)
