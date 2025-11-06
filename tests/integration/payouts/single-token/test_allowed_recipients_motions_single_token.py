import pytest

from brownie import reverts
from brownie.network import chain

from utils import evm_script, test_helpers
from utils.dual_governance import submit_proposals, process_pending_proposals

MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60


def test_add_recipient_motion(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
):
    recipient = recipients[0]

    allowed_recipients_count_before = len(allowed_recipients_registry.getAllowedRecipients())

    motion_enactment_tx = add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory, recipient.address, recipient.title
    )
    test_helpers.assert_event_exists(
        motion_enactment_tx,
        "RecipientAdded",
        {"_recipient": recipient.address, "_title": recipient.title},
    )
    assert len(allowed_recipients_registry.getAllowedRecipients()) == allowed_recipients_count_before + 1


def test_add_multiple_recipients_by_concurrent_motions(
    recipients,
    easy_track,
    allowed_recipients_registry,
    enact_motion_by_creation_tx,
    create_add_allowed_recipient_motion,
    add_allowed_recipient_evm_script_factory,
):
    first_recipient, second_recipient = recipients[:2]

    allowed_recipients_count_before = len(allowed_recipients_registry.getAllowedRecipients())

    first_motion_creation_tx = create_add_allowed_recipient_motion(
        add_allowed_recipient_evm_script_factory,
        first_recipient.address,
        first_recipient.title,
    )

    second_motion_creation_tx = create_add_allowed_recipient_motion(
        add_allowed_recipient_evm_script_factory,
        second_recipient.address,
        second_recipient.title,
    )

    chain.sleep(easy_track.motionDuration() + 100)

    enact_motion_by_creation_tx(first_motion_creation_tx)
    enact_motion_by_creation_tx(second_motion_creation_tx)

    assert allowed_recipients_registry.isRecipientAllowed(first_recipient.address)
    assert allowed_recipients_registry.isRecipientAllowed(second_recipient.address)
    assert len(allowed_recipients_registry.getAllowedRecipients()) == allowed_recipients_count_before + 2


def test_fail_add_same_recipient_by_second_concurrent_motion(
    recipients,
    easy_track,
    enact_motion_by_creation_tx,
    create_add_allowed_recipient_motion,
    add_allowed_recipient_evm_script_factory,
):
    recipient = recipients[0]

    first_motion_creation_tx = create_add_allowed_recipient_motion(
        add_allowed_recipient_evm_script_factory,
        recipient.address,
        recipient.title,
    )

    second_motion_creation_tx = create_add_allowed_recipient_motion(
        add_allowed_recipient_evm_script_factory,
        recipient.address,
        recipient.title,
    )

    chain.sleep(easy_track.motionDuration() + 100)

    enact_motion_by_creation_tx(first_motion_creation_tx)

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        enact_motion_by_creation_tx(second_motion_creation_tx)


def test_fail_if_add_same_recipient_twice(
    recipients,
    add_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
):
    allowed_recipient = recipients[0]
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipient.address,
        allowed_recipient.title,
    )

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        add_allowed_recipient_by_motion(
            add_allowed_recipient_evm_script_factory,
            allowed_recipient.address,
            allowed_recipient.title,
        )


def test_remove_recipient_motion(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    remove_allowed_recipient_evm_script_factory,
    remove_allowed_recipient_by_motion,
):
    allowed_recipient = recipients[0]

    allowed_recipients_count_before = len(allowed_recipients_registry.getAllowedRecipients())

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipient.address,
        allowed_recipient.title,
    )

    motion_enactment_tx = remove_allowed_recipient_by_motion(
        remove_allowed_recipient_evm_script_factory, allowed_recipient.address
    )

    test_helpers.assert_event_exists(
        motion_enactment_tx,
        "RecipientRemoved",
        {"_recipient": allowed_recipient.address},
    )

    assert len(allowed_recipients_registry.getAllowedRecipients()) == allowed_recipients_count_before


def test_fail_remove_recipient_if_empty_allowed_recipients_list(
    recipients,
    allowed_recipients_registry,
    remove_allowed_recipient_by_motion,
    remove_allowed_recipient_evm_script_factory,
):

    allowed_recipients = allowed_recipients_registry.getAllowedRecipients()
    for allowed_recipient in allowed_recipients:
        remove_allowed_recipient_by_motion(remove_allowed_recipient_evm_script_factory, allowed_recipient)

    assert len(allowed_recipients_registry.getAllowedRecipients()) == 0

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_allowed_recipient_by_motion(remove_allowed_recipient_evm_script_factory, recipients[0].address)


def test_fail_remove_recipient_if_it_is_not_allowed(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    remove_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    remove_allowed_recipient_evm_script_factory,
):
    allowed_recipient, not_allowed_recipient = recipients[0], recipients[1]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipient.address,
        allowed_recipient.title,
    )

    assert len(allowed_recipients_registry.getAllowedRecipients()) > 0
    assert not allowed_recipients_registry.isRecipientAllowed(not_allowed_recipient.address)

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_allowed_recipient_by_motion(remove_allowed_recipient_evm_script_factory, not_allowed_recipient.address)


def test_top_up_single_recipient(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipient = recipients[0]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipient.address,
        allowed_recipient.title,
    )

    top_up_recipient_addresses = [allowed_recipient.address]
    top_up_amounts = [2 * 10**18]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        top_up_recipient_addresses,
        top_up_amounts,
    )


def test_top_up_single_recipient_several_times_in_period(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipient = recipients[0]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipient.address,
        allowed_recipient.title,
    )

    top_up_recipient_addresses = [allowed_recipient.address]
    top_up_amounts = [int(allowed_recipients_limit_params.limit / 2)]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        top_up_recipient_addresses,
        top_up_amounts,
    )

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory, top_up_recipient_addresses, top_up_amounts, sum(top_up_amounts)
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(
            top_up_allowed_recipients_evm_script_factory,
            top_up_recipient_addresses,
            [1],
        )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        top_up_recipient_addresses,
        [allowed_recipients_limit_params.limit],
    )


def test_top_up_multiple_recipients(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    top_up_amounts = [2 * 10**18, 1 * 10**18]

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )


def test_top_up_motion_enacted_in_next_period(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    top_up_amounts = [int(3e18), int(90e18)]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )

    # Wait for next period
    chain.sleep(allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx)


def test_top_up_motion_ended_and_enacted_in_next_period(
    recipients,
    easy_track,
    allowed_recipients_limit_params,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    top_up_amounts = [int(3e18), int(90e18)]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)
    test_helpers.advance_chain_time_to_n_seconds_before_current_period_end(
        allowed_recipients_limit_params.duration, easy_track.motionDuration() // 2
    )

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )

    _, _, *old_period_range = allowed_recipients_registry.getPeriodState()

    enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx)

    _, _, *new_period_range = allowed_recipients_registry.getPeriodState()
    assert (
        old_period_range != new_period_range
    ), "check periods when the motion was created and when it ended are different"


def test_top_up_motion_enacted_in_second_next_period(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    top_up_amounts = [int(3e18), int(90e18)]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )

    chain.sleep(2 * allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx)


def test_spendable_balance_is_renewed_in_next_period(
    recipients,
    allowed_recipients_limit_params,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
):
    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    assert allowed_recipients_registry.spendableBalance() == allowed_recipients_limit_params.limit

    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    top_up_amounts = [
        int(allowed_recipients_limit_params.limit // 10**18 * 0.1) * 10**18,
        int(allowed_recipients_limit_params.limit // 10**18 * 0.9) * 10**18,
    ]

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )

    amount_spent = sum(top_up_amounts)
    assert allowed_recipients_registry.getPeriodState()[0] == amount_spent
    assert allowed_recipients_registry.spendableBalance() == allowed_recipients_limit_params.limit - amount_spent

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(
            top_up_allowed_recipients_evm_script_factory,
            [allowed_recipients[0].address],
            [1],
        )

    chain.sleep(allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    # cannot just check the views `spendableBalance` and `getPeriodState`
    # because they are not updated without a call of updateSpentAmount
    # or setLimitParameters. So trying to make a full period limit amount payout
    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        [allowed_recipients[0].address],
        [allowed_recipients_limit_params.limit],
    )

    assert allowed_recipients_registry.getPeriodState()[0] == allowed_recipients_limit_params.limit
    assert allowed_recipients_registry.spendableBalance() == 0


def test_fail_enact_top_up_motion_if_recipient_removed_by_other_motion(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    remove_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    remove_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    recipient_to_remove = allowed_recipients[0]
    top_up_amounts = [int(40e18), int(30e18)]

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )

    remove_allowed_recipient_by_motion(remove_allowed_recipient_evm_script_factory, recipient_to_remove.address)

    with reverts("RECIPIENT_NOT_ALLOWED"):
        enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx)


def test_fail_create_top_up_motion_if_exceeds_limit(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipient = recipients[0]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipient.address,
        allowed_recipient.title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        exceeded_top_up_amounts = [allowed_recipients_limit_params.limit + 1]
        create_top_up_allowed_recipients_motion(
            top_up_allowed_recipients_evm_script_factory,
            [allowed_recipient.address],
            exceeded_top_up_amounts,
        )


def test_fail_to_create_top_up_motion_which_exceeds_spendable(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    first_top_up_amounts = [
        int(allowed_recipients_limit_params.limit // 10**18 * 0.4) * 10**18,
        int(allowed_recipients_limit_params.limit // 10**18 * 0.6) * 10**18,
    ]

    assert sum(first_top_up_amounts) == allowed_recipients_limit_params.limit

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        first_top_up_amounts,
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        second_top_up_amounts = [1, 1]
        top_up_allowed_recipient_by_motion(
            top_up_allowed_recipients_evm_script_factory,
            [r.address for r in allowed_recipients],
            second_top_up_amounts,
        )


def test_fail_2nd_top_up_motion_enactment_due_limit_but_can_enact_in_next(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    first_top_up_amount = [
        int(allowed_recipients_limit_params.limit // 10**18 * 0.4) * 10**18,
        int(allowed_recipients_limit_params.limit // 10**18 * 0.3) * 10**18,
    ]
    second_top_up_amount = [
        int(allowed_recipients_limit_params.limit // 10**18 * 0.3) * 10**18,
        int(allowed_recipients_limit_params.limit // 10**18 * 0.2) * 10**18,
    ]

    assert sum(first_top_up_amount + second_top_up_amount) > allowed_recipients_limit_params.limit
    first_motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        first_top_up_amount,
    )
    second_motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        second_top_up_amount,
    )

    enact_top_up_allowed_recipient_motion_by_creation_tx(first_motion_creation_tx)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        enact_top_up_allowed_recipient_motion_by_creation_tx(second_motion_creation_tx)

    chain.sleep(allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    enact_top_up_allowed_recipient_motion_by_creation_tx(second_motion_creation_tx)


def test_fail_2nd_top_up_motion_creation_in_period_if_it_exceeds_spendable(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    allowed_recipients_limit_params,
    top_up_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
):
    """Revert 2nd payout which together with 1st payout exceed the current period limit"""

    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    first_top_up_amounts = [
        int(allowed_recipients_limit_params.limit // 10**18 * 0.03) * 10**18,
        int(allowed_recipients_limit_params.limit // 10**18 * 0.9) * 10**18,
    ]
    second_top_up_amounts = [
        int(allowed_recipients_limit_params.limit // 10**18 * 0.05) * 10**18,
        int(allowed_recipients_limit_params.limit // 10**18 * 0.04) * 10**18,
    ]

    assert sum(first_top_up_amounts + second_top_up_amounts) > allowed_recipients_limit_params.limit

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        first_top_up_amounts,
    )

    assert sum(second_top_up_amounts) > allowed_recipients_registry.spendableBalance()

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(
            top_up_allowed_recipients_evm_script_factory,
            [r.address for r in allowed_recipients],
            second_top_up_amounts,
        )


def test_fail_top_up_if_limit_decreased_while_motion_is_in_flight(
    recipients,
    lido_contracts,
    allowed_recipients_registry,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    allowed_recipients = recipients[:1]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    top_up_amounts = [allowed_recipients_limit_params.limit]
    motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )

    allowed_recipients_registry.setLimitParameters(
        allowed_recipients_limit_params.limit // 2,
        allowed_recipients_limit_params.duration,
        {"from": lido_contracts.aragon.agent},
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx)


def test_top_up_if_limit_increased_while_motion_is_in_flight(
    recipients,
    lido_contracts,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    allowed_recipients_limit_params,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):

    allowed_recipients = recipients[:1]
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    top_up_amounts = [allowed_recipients_limit_params.limit]
    motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        top_up_amounts,
    )

    allowed_recipients_registry.setLimitParameters(
        3 * allowed_recipients_limit_params.limit,
        allowed_recipients_limit_params.duration,
        {"from": lido_contracts.aragon.agent},
    )

    enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx)


def test_two_motion_seconds_failed_to_enact_due_limit_but_succeeded_after_limit_increased(
    easy_track,
    recipients,
    lido_contracts,
    enact_motion_by_creation_tx,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    allowed_recipients_limit_params,
    create_top_up_allowed_recipients_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )
    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[1].address,
        allowed_recipients[1].title,
    )

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(allowed_recipients_limit_params.duration)

    first_top_up_amounts = [
        int(allowed_recipients_limit_params.limit // 10**18 * 0.4) * 10**18,
        int(allowed_recipients_limit_params.limit // 10**18 * 0.6) * 10**18,
    ]
    assert sum(first_top_up_amounts) == allowed_recipients_limit_params.limit
    second_top_up_amounts = [1, 1]

    first_motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        first_top_up_amounts,
    )

    second_motion_creation_tx = create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        second_top_up_amounts,
    )

    enact_top_up_allowed_recipient_motion_by_creation_tx(first_motion_creation_tx)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        enact_top_up_allowed_recipient_motion_by_creation_tx(second_motion_creation_tx)

    allowed_recipients_registry.setLimitParameters(
        allowed_recipients_limit_params.limit + sum(second_top_up_amounts),
        allowed_recipients_limit_params.duration,
        {"from": lido_contracts.aragon.agent},
    )

    chain.sleep(easy_track.motionDuration() + 100)

    # We don't run check_top_up_motion_enactment fixture because
    # was another payment in the same period and check will fail
    enact_motion_by_creation_tx(second_motion_creation_tx)


@pytest.mark.parametrize("initial_period_duration,new_period_duration", [(3, 2), (3, 6), (12, 1), (1, 12)])
def test_top_up_spendable_renewal_if_period_duration_changed(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    lido_contracts,
    create_top_up_allowed_recipients_motion,
    top_up_allowed_recipient_by_motion,
    add_allowed_recipient_evm_script_factory,
    top_up_allowed_recipients_evm_script_factory,
    initial_period_duration: int,
    new_period_duration: int,
):
    period_limit = 100 * 10**18
    allowed_recipients = recipients[:1]

    add_allowed_recipient_by_motion(
        add_allowed_recipient_evm_script_factory,
        allowed_recipients[0].address,
        allowed_recipients[0].title,
    )

    first_top_up_amount = [period_limit]
    second_top_up_amount = [1]  # just 1 wei

    allowed_recipients_registry.setLimitParameters(
        period_limit, initial_period_duration, {"from": lido_contracts.aragon.agent}
    )
    test_helpers.advance_chain_time_to_middle_of_the_next_period(initial_period_duration)

    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        first_top_up_amount,
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_allowed_recipients_motion(
            top_up_allowed_recipients_evm_script_factory,
            [r.address for r in allowed_recipients],
            second_top_up_amount,
        )

    allowed_recipients_registry.setLimitParameters(
        period_limit, new_period_duration, {"from": lido_contracts.aragon.agent}
    )

    # expect it to revert because although calendar grid period has changed
    # the amount spent and the limit are left intact
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_allowed_recipients_motion(
            top_up_allowed_recipients_evm_script_factory,
            [r.address for r in allowed_recipients],
            second_top_up_amount,
        )

    test_helpers.advance_chain_time_to_middle_of_the_next_period(new_period_duration)

    # when move time to time point in the next period of the new calendar period grid
    # expect the spendable get renewed
    top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory,
        [r.address for r in allowed_recipients],
        second_top_up_amount,
    )


def test_set_limit_parameters_by_aragon_agent_via_voting(lido_contracts, allowed_recipients_registry):
    """Do Aragon Agent to set limit parameters to the allowed recipients registry"""
    period_limit, period_duration = 100 * 10**18, 6

    set_limit_parameters_voting_id, _ = lido_contracts.create_voting(
        evm_script=evm_script.encode_call_script(
            submit_proposals(
                [
                    (
                        [
                            (
                                lido_contracts.aragon.agent.address,
                                lido_contracts.aragon.agent.forward.encode_input(
                                    evm_script.encode_call_script(
                                        [
                                            (
                                                allowed_recipients_registry.address,
                                                allowed_recipients_registry.setLimitParameters.encode_input(
                                                    period_limit,
                                                    period_duration,
                                                ),
                                            )
                                        ]
                                    )
                                ),
                            )
                        ],
                        "Set limit parameters",
                    )
                ]
            )
        ),
        description="Set limit parameters",
        tx_params={"from": lido_contracts.aragon.agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    lido_contracts.execute_voting(set_limit_parameters_voting_id)
    process_pending_proposals()

    assert allowed_recipients_registry.getLimitParameters() == (
        period_limit,
        period_duration,
    )