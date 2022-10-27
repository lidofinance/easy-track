from brownie.network import chain
from brownie import reverts, interface
import pytest

from eth_abi import encode_single
from utils.evm_script import encode_calldata

from conftest import (
    AllowedRecipientsSetup,
    AllowedRecipientsSetupWithTwoRecipients,
)

from utils.allowed_recipients_motions import (
    add_recipient_by_motion,
    remove_recipient_by_motion,
    create_top_up_motion,
    do_payout_to_allowed_recipients_by_motion,
    get_balances,
    check_top_up,
)

from utils.test_helpers import (
    assert_event_exists,
    advance_chain_time_to_beginning_of_the_next_period,
    advance_chain_time_to_n_seconds_before_current_period_end,
)

import constants


MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60
DEFAULT_PERIOD_DURATION_MONTHS = 3


def test_add_recipient_motion(entire_allowed_recipients_setup: AllowedRecipientsSetup, accounts):
    setup = entire_allowed_recipients_setup

    recipient = accounts[8]
    recipient_title = "New Allowed Recipient"

    call_data = encode_calldata("(address,string)", [recipient.address, recipient_title])
    assert setup.add_recipient_factory.decodeEVMScriptCallData(call_data) == [
        recipient.address,
        recipient_title,
    ]

    tx = setup.easy_track.createMotion(
        setup.add_recipient_factory,
        call_data,
        {"from": setup.add_recipient_factory.trustedCaller()},
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    tx = setup.easy_track.enactMotion(
        setup.easy_track.getMotions()[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": recipient},
    )
    assert_event_exists(
        tx,
        "RecipientAdded",
        {"_recipient": recipient, "_title": recipient_title},
    )
    assert setup.registry.isRecipientAllowed(recipient)
    assert len(setup.registry.getAllowedRecipients()) == 1


def test_add_multiple_recipients_by_concurrent_motions(
    entire_allowed_recipients_setup: AllowedRecipientsSetup, accounts
):
    setup = entire_allowed_recipients_setup

    recipient1 = accounts[8].address
    recipient1_title = "New Allowed Recipient #1"
    recipient2 = accounts[9].address
    recipient2_title = "New Allowed Recipient #2"

    tx = setup.easy_track.createMotion(
        setup.add_recipient_factory,
        encode_calldata("(address,string)", [recipient1, recipient1_title]),
        {"from": setup.add_recipient_factory.trustedCaller()},
    )
    motion1_id = tx.events["MotionCreated"]["_motionId"]
    motion1_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    tx = setup.easy_track.createMotion(
        setup.add_recipient_factory,
        encode_calldata("(address,string)", [recipient2, recipient2_title]),
        {"from": setup.add_recipient_factory.trustedCaller()},
    )
    motion2_id = tx.events["MotionCreated"]["_motionId"]
    motion2_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    # Enact in reverse order just to check that order in the registry
    # depends on the order of motions enactment but order of creation
    setup.easy_track.enactMotion(motion2_id, motion2_calldata, {"from": setup.easy_track})
    setup.easy_track.enactMotion(motion1_id, motion1_calldata, {"from": setup.easy_track})

    assert setup.registry.isRecipientAllowed(recipient1)
    assert setup.registry.isRecipientAllowed(recipient2)
    assert setup.registry.getAllowedRecipients() == [recipient2, recipient1]


def test_fail_add_same_recipient_by_second_concurrent_motion(
    entire_allowed_recipients_setup: AllowedRecipientsSetup, accounts
):
    setup = entire_allowed_recipients_setup

    recipient = accounts[8].address
    recipient_title = "New Allowed Recipient #1"

    tx = setup.easy_track.createMotion(
        setup.add_recipient_factory,
        encode_calldata("(address,string)", [recipient, recipient_title]),
        {"from": setup.add_recipient_factory.trustedCaller()},
    )
    motion1_id = tx.events["MotionCreated"]["_motionId"]
    motion1_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    tx = setup.easy_track.createMotion(
        setup.add_recipient_factory,
        encode_calldata("(address,string)", [recipient, recipient_title]),
        {"from": setup.add_recipient_factory.trustedCaller()},
    )
    motion2_id = tx.events["MotionCreated"]["_motionId"]
    motion2_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    setup.easy_track.enactMotion(motion1_id, motion1_calldata, {"from": setup.easy_track})

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        setup.easy_track.enactMotion(motion2_id, motion2_calldata, {"from": setup.easy_track})


def test_fail_if_add_same_recipient_twice(
    entire_allowed_recipients_setup: AllowedRecipientsSetup, accounts
):
    setup = entire_allowed_recipients_setup

    recipient = accounts[8]
    recipient_title = "New Allowed Recipient"

    add_recipient_by_motion(
        recipient, recipient_title, setup.easy_track, setup.add_recipient_factory
    )

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        add_recipient_by_motion(
            recipient, recipient_title, setup.easy_track, setup.add_recipient_factory
        )


def test_remove_recipient_motion(entire_allowed_recipients_setup: AllowedRecipientsSetup, accounts):
    setup = entire_allowed_recipients_setup

    recipient = accounts[8]
    recipient_title = "New Allowed Recipient"

    add_recipient_by_motion(
        recipient, recipient_title, setup.easy_track, setup.add_recipient_factory
    )
    assert len(setup.registry.getAllowedRecipients()) == 1

    call_data = encode_single("(address)", [recipient.address])
    assert setup.remove_recipient_factory.decodeEVMScriptCallData(call_data) == recipient.address

    tx = setup.easy_track.createMotion(
        setup.remove_recipient_factory,
        call_data,
        {"from": setup.remove_recipient_factory.trustedCaller()},
    )

    assert tx.events["MotionCreated"]["_evmScriptCallData"] == "0x" + call_data.hex()

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    tx = setup.easy_track.enactMotion(
        setup.easy_track.getMotions()[0][0],
        call_data,
        {"from": recipient},
    )
    assert_event_exists(
        tx,
        "RecipientRemoved",
        {"_recipient": recipient},
    )
    assert not setup.registry.isRecipientAllowed(recipient)
    assert len(setup.registry.getAllowedRecipients()) == 0


def test_fail_remove_recipient_if_empty_allowed_recipients_list(
    entire_allowed_recipients_setup: AllowedRecipientsSetup, accounts
):
    setup = entire_allowed_recipients_setup

    recipient = accounts[8]
    assert len(setup.registry.getAllowedRecipients()) == 0

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_recipient_by_motion(
            recipient,
            setup.easy_track,
            setup.remove_recipient_factory,
            setup.registry,
        )


def test_fail_remove_recipient_if_it_is_not_allowed(
    entire_allowed_recipients_setup: AllowedRecipientsSetup, accounts, stranger
):
    setup = entire_allowed_recipients_setup

    add_recipient_by_motion(
        accounts[8], "Allowed Recipient", setup.easy_track, setup.add_recipient_factory
    )

    assert len(setup.registry.getAllowedRecipients()) > 0
    assert not setup.registry.isRecipientAllowed(stranger)

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_recipient_by_motion(
            stranger,
            setup.easy_track,
            setup.remove_recipient_factory,
            setup.registry,
        )


def test_top_up_single_recipient(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    agent,
):
    setup = entire_allowed_recipients_setup_with_two_recipients
    recipients = [setup.recipient1.address]
    amounts = [2 * 10**18]

    period_limit = 3 * 10**18
    period_duration = DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    script_call_data = encode_single("(address[],uint256[])", [recipients, amounts])
    tx = setup.easy_track.createMotion(
        setup.top_up_factory,
        script_call_data,
        {"from": setup.top_up_factory.trustedCaller()},
    )
    motion_id = tx.events["MotionCreated"]["_motionId"]

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    balances_before = get_balances(recipients, setup.top_up_factory.token())
    agent_balance_before = interface.ERC20(setup.top_up_factory.token()).balanceOf(agent)
    tx = setup.easy_track.enactMotion(motion_id, script_call_data, {"from": setup.recipient1})
    check_top_up(
        tx,
        agent_balance_before,
        balances_before,
        recipients,
        amounts,
        setup.registry,
        setup.top_up_factory,
        agent,
    )


def test_top_up_multiple_recipients(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    agent,
):
    setup = entire_allowed_recipients_setup_with_two_recipients
    recipients = [setup.recipient1.address, setup.recipient2.address]
    amounts = [2 * 10**18, 1 * 10**18]

    period_limit = 4 * 10**18
    period_duration = DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    script_call_data = encode_single("(address[],uint256[])", [recipients, amounts])
    tx = setup.easy_track.createMotion(
        setup.top_up_factory,
        script_call_data,
        {"from": setup.top_up_factory.trustedCaller()},
    )
    motion_id = tx.events["MotionCreated"]["_motionId"]

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    balances_before = get_balances(recipients, setup.top_up_factory.token())
    agent_balance_before = interface.ERC20(setup.top_up_factory.token()).balanceOf(agent)
    tx = setup.easy_track.enactMotion(motion_id, script_call_data, {"from": setup.recipient1})
    check_top_up(
        tx,
        agent_balance_before,
        balances_before,
        recipients,
        amounts,
        setup.registry,
        setup.top_up_factory,
        agent,
    )


def test_top_up_motion_enacted_in_next_period(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    agent,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    payouts = [int(3e18), int(90e18)]
    recipients = [setup.recipient1.address, setup.recipient2.address]

    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    motion_id, script_call_data = create_top_up_motion(
        recipients, payouts, setup.easy_track, setup.top_up_factory
    )

    chain.sleep(period_duration * MAX_SECONDS_IN_MONTH)

    balances_before = get_balances(recipients, setup.top_up_factory.token())
    agent_balance_before = interface.ERC20(setup.top_up_factory.token()).balanceOf(agent)
    tx = setup.easy_track.enactMotion(motion_id, script_call_data, {"from": setup.recipient1})
    check_top_up(
        tx,
        agent_balance_before,
        balances_before,
        recipients,
        payouts,
        setup.registry,
        setup.top_up_factory,
        agent,
    )


def test_top_up_motion_ended_and_enacted_in_next_period(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    agent,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    payouts = [int(3e18), int(90e18)]
    recipients = [setup.recipient1.address, setup.recipient2.address]

    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)
    advance_chain_time_to_n_seconds_before_current_period_end(
        period_duration, constants.MIN_MOTION_DURATION // 2
    )

    motion_id, script_call_data = create_top_up_motion(
        recipients, payouts, setup.easy_track, setup.top_up_factory
    )

    _, _, *old_period_range = setup.registry.getPeriodState()

    chain.sleep(constants.MIN_MOTION_DURATION)

    balances_before = get_balances(recipients, setup.top_up_factory.token())
    agent_balance_before = interface.ERC20(setup.top_up_factory.token()).balanceOf(agent)
    tx = setup.easy_track.enactMotion(motion_id, script_call_data, {"from": setup.recipient1})
    check_top_up(
        tx,
        agent_balance_before,
        balances_before,
        recipients,
        payouts,
        setup.registry,
        setup.top_up_factory,
        agent,
    )
    _, _, *new_period_range = setup.registry.getPeriodState()
    assert (
        old_period_range != new_period_range
    ), "check periods when the motion was created and when it ended are different"


def test_top_up_motion_enacted_in_second_next_period(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    agent,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    payouts = [int(3e18), int(90e18)]
    recipients = [setup.recipient1.address, setup.recipient2.address]

    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    motion_id, script_call_data = create_top_up_motion(
        recipients, payouts, setup.easy_track, setup.top_up_factory
    )

    chain.sleep(2 * period_duration * MAX_SECONDS_IN_MONTH)

    balances_before = get_balances(recipients, setup.top_up_factory.token())
    agent_balance_before = interface.ERC20(setup.top_up_factory.token()).balanceOf(agent)
    tx = setup.easy_track.enactMotion(motion_id, script_call_data, {"from": setup.recipient1})
    check_top_up(
        tx,
        agent_balance_before,
        balances_before,
        recipients,
        payouts,
        setup.registry,
        setup.top_up_factory,
        agent,
    )


def test_spendable_balance_is_renewed_in_next_period(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    assert setup.registry.spendableBalance() == period_limit

    payout_amounts = [int(10e18), int(90e18)]
    recipients = [setup.recipient1.address, setup.recipient2.address]
    do_payout_to_allowed_recipients_by_motion(
        recipients, payout_amounts, setup.easy_track, setup.top_up_factory
    )

    amount_spent = sum(payout_amounts)
    assert setup.registry.getPeriodState()[0] == amount_spent
    assert setup.registry.spendableBalance() == period_limit - amount_spent

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        do_payout_to_allowed_recipients_by_motion(
            [setup.recipient1.address], [1], setup.easy_track, setup.top_up_factory
        )

    chain.sleep(period_duration * MAX_SECONDS_IN_MONTH)

    # cannot just check the views `spendableBalance` and `getPeriodState`
    # because they are not updated without a call of updateSpentAmount
    # or setLimitParameters. So trying to make a full period limit amount payout
    do_payout_to_allowed_recipients_by_motion(
        [setup.recipient1.address], [period_limit], setup.easy_track, setup.top_up_factory
    )
    assert setup.registry.getPeriodState()[0] == period_limit
    assert setup.registry.spendableBalance() == 0


def test_fail_enact_top_up_motion_if_recipient_removed_by_other_motion(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    recipients = [setup.recipient1.address, setup.recipient2.address]
    payout = [int(40e18), int(30e18)]
    motion1_id, motion1_calldata = create_top_up_motion(
        recipients, payout, setup.easy_track, setup.top_up_factory
    )

    remove_recipient_by_motion(
        setup.recipient1, setup.easy_track, setup.remove_recipient_factory, setup.registry
    )

    with reverts("RECIPIENT_NOT_ALLOWED"):
        setup.easy_track.enactMotion(motion1_id, motion1_calldata, {"from": setup.recipient1})


def test_fail_create_top_up_motion_if_exceeds_limit(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_motion(
            [setup.recipient1.address], [period_limit + 1], setup.easy_track, setup.top_up_factory
        )


def test_create_top_up_motion_which_exceeds_spendable_if_motion_ends_in_next_period(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    setup = entire_allowed_recipients_setup_with_two_recipients
    recipients = [setup.recipient1.address, setup.recipient2.address]

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    payout1 = [int(40e18), int(50e18)]

    do_payout_to_allowed_recipients_by_motion(
        recipients, payout1, setup.easy_track, setup.top_up_factory
    )

    payout2 = [int(10e18), 1]
    assert sum(payout1) + sum(payout2) > period_limit

    advance_chain_time_to_n_seconds_before_current_period_end(
        period_duration, constants.MIN_MOTION_DURATION // 2
    )

    create_top_up_motion(recipients, payout2, setup.easy_track, setup.top_up_factory)


def test_fail_to_create_top_up_motion_which_exceeds_spendable_if_motion_ends_in_this_period(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    setup = entire_allowed_recipients_setup_with_two_recipients
    recipients = [setup.recipient1.address, setup.recipient2.address]

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    payout1 = [int(40e18), int(50e18)]

    do_payout_to_allowed_recipients_by_motion(
        recipients, payout1, setup.easy_track, setup.top_up_factory
    )

    payout2 = [int(10e18), 1]
    assert sum(payout1) + sum(payout2) > period_limit
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_motion(recipients, payout2, setup.easy_track, setup.top_up_factory)


def test_fail_2nd_top_up_motion_enactment_due_limit_but_can_enact_in_next(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    setup = entire_allowed_recipients_setup_with_two_recipients
    recipients = [setup.recipient1.address, setup.recipient2.address]

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    payout1 = [int(40e18), int(30e18)]
    payout2 = [int(30e18), int(20e18)]
    assert sum(payout1 + payout2) > period_limit
    motion1_id, motion1_calldata = create_top_up_motion(
        recipients, payout1, setup.easy_track, setup.top_up_factory
    )
    motion2_id, motion2_calldata = create_top_up_motion(
        recipients, payout2, setup.easy_track, setup.top_up_factory
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    setup.easy_track.enactMotion(motion1_id, motion1_calldata, {"from": setup.recipient1})

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        setup.easy_track.enactMotion(motion2_id, motion2_calldata, {"from": setup.recipient1})

    chain.sleep(period_duration * MAX_SECONDS_IN_MONTH)

    setup.easy_track.enactMotion(motion2_id, motion2_calldata, {"from": setup.recipient1})


def test_fail_2nd_top_up_motion_creation_in_period_if_it_exceeds_spendable(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    """Revert 2nd payout which together with 1st payout exceed the current period limit"""
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)
    payout1 = [int(3e18), int(90e18)]
    payout2 = [int(5e18), int(4e18)]
    assert sum(payout1 + payout2) > period_limit

    recipients = list(map(lambda x: x.address, [setup.recipient1, setup.recipient2]))
    do_payout_to_allowed_recipients_by_motion(
        recipients, payout1, setup.easy_track, setup.top_up_factory
    )
    assert sum(payout2) > setup.registry.spendableBalance()

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_motion(recipients, payout2, setup.easy_track, setup.top_up_factory)


def test_fail_top_up_if_limit_decreased_while_motion_is_in_flight(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    motion_id, motion_calldata = create_top_up_motion(
        [setup.recipient1.address], [period_limit], setup.easy_track, setup.top_up_factory
    )

    setup.registry.setLimitParameters(
        period_limit // 2, period_duration, {"from": setup.evm_script_executor}
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        setup.easy_track.enactMotion(motion_id, motion_calldata, {"from": setup.recipient1})


def test_top_up_if_limit_increased_while_motion_is_in_flight(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    agent,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    recipients = [setup.recipient1.address]
    payouts = [period_limit]
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    motion_id, motion_calldata = create_top_up_motion(
        recipients, payouts, setup.easy_track, setup.top_up_factory
    )

    setup.registry.setLimitParameters(
        3 * period_limit, period_duration, {"from": setup.evm_script_executor}
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    balances_before = get_balances(recipients, setup.top_up_factory.token())
    agent_balance_before = interface.ERC20(setup.top_up_factory.token()).balanceOf(agent)
    tx = setup.easy_track.enactMotion(motion_id, motion_calldata, {"from": setup.recipient1})
    check_top_up(
        tx,
        agent_balance_before,
        balances_before,
        recipients,
        payouts,
        setup.registry,
        setup.top_up_factory,
        agent,
    )


def test_two_motions_second_failed_to_enact_due_limit_but_succeeded_after_limit_increased(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    stranger,
):
    setup = entire_allowed_recipients_setup_with_two_recipients
    recipients = [setup.recipient1.address, setup.recipient2.address]

    period_limit, period_duration = 100 * 10**18, DEFAULT_PERIOD_DURATION_MONTHS
    setup.registry.setLimitParameters(
        period_limit, period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(period_duration)

    payout1 = [int(40e18), int(60e18)]
    assert sum(payout1) == period_limit
    payout2 = [1, 1]
    motion1_id, motion1_calldata = create_top_up_motion(
        recipients, payout1, setup.easy_track, setup.top_up_factory
    )
    motion2_id, motion2_calldata = create_top_up_motion(
        recipients, payout2, setup.easy_track, setup.top_up_factory
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    setup.easy_track.enactMotion(motion1_id, motion1_calldata, {"from": stranger})

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        setup.easy_track.enactMotion(motion2_id, motion2_calldata, {"from": stranger})

    setup.registry.setLimitParameters(
        period_limit + sum(payout2), period_duration, {"from": setup.evm_script_executor}
    )

    setup.easy_track.enactMotion(motion2_id, motion2_calldata, {"from": stranger})


@pytest.mark.parametrize(
    "initial_period_duration,new_period_duration", [(3, 2), (3, 6), (12, 1), (1, 12)]
)
def test_top_up_spendable_renewal_if_period_duration_changed(
    entire_allowed_recipients_setup_with_two_recipients: AllowedRecipientsSetupWithTwoRecipients,
    initial_period_duration: int,
    new_period_duration: int,
):
    setup = entire_allowed_recipients_setup_with_two_recipients

    period_limit = 100 * 10**18
    recipients = [setup.recipient1.address]
    first_payout = [period_limit]
    second_payout = [1]  # just 1 wei

    setup.registry.setLimitParameters(
        period_limit, initial_period_duration, {"from": setup.evm_script_executor}
    )
    advance_chain_time_to_beginning_of_the_next_period(initial_period_duration)

    do_payout_to_allowed_recipients_by_motion(
        recipients, first_payout, setup.easy_track, setup.top_up_factory
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_motion(
            [setup.recipient1.address], second_payout, setup.easy_track, setup.top_up_factory
        )

    setup.registry.setLimitParameters(
        period_limit, new_period_duration, {"from": setup.evm_script_executor}
    )

    # expect it to revert because although calendar grid period has changed
    # the amount spent and the limit are left intact
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_motion(
            [setup.recipient1.address], second_payout, setup.easy_track, setup.top_up_factory
        )

    advance_chain_time_to_beginning_of_the_next_period(new_period_duration)

    # when move time to time point in the next period of the new calendar period grid
    # expect the spendable get renewed
    do_payout_to_allowed_recipients_by_motion(
        recipients, second_payout, setup.easy_track, setup.top_up_factory
    )
