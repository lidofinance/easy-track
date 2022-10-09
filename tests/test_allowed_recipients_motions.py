from brownie.network import chain
from brownie import reverts

from eth_abi import encode_single
from utils.evm_script import encode_calldata


from utils.allowed_recipients_motions import (
    add_recipient_by_motion,
    remove_recipient_by_motion,
    create_top_up_motion,
    set_limit_parameters_by_aragon_voting,
    do_payout_to_allowed_recipients_by_motion,
)

from utils.test_helpers import (
    assert_event_exists,
)

import constants


MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60


def test_add_recipient_motion(entire_allowed_recipients_setup, accounts):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        _,  # top_up_factory,
        add_recipient_factory,
        _,  # remove_recipient_factory,
    ) = entire_allowed_recipients_setup

    recipient = accounts[8]
    recipient_title = "New Allowed Recipient"

    call_data = encode_calldata("(address,string)", [recipient.address, recipient_title])
    assert add_recipient_factory.decodeEVMScriptCallData(call_data) == [
        recipient.address,
        recipient_title,
    ]

    tx = easy_track.createMotion(
        add_recipient_factory,
        call_data,
        {"from": add_recipient_factory.trustedCaller()},
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    tx = easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": recipient},
    )
    assert_event_exists(
        tx,
        "RecipientAdded",
        {"_recipient": recipient, "_title": recipient_title},
    )
    assert allowed_recipients_registry.isRecipientAllowed(recipient)
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 1


def test_add_multiple_recipients_by_concurrent_motions(entire_allowed_recipients_setup, accounts):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        _,  # top_up_factory,
        add_recipient_factory,
        _,
    ) = entire_allowed_recipients_setup

    recipient1 = accounts[8].address
    recipient1_title = "New Allowed Recipient #1"
    recipient2 = accounts[9].address
    recipient2_title = "New Allowed Recipient #2"

    tx = easy_track.createMotion(
        add_recipient_factory,
        encode_calldata("(address,string)", [recipient1, recipient1_title]),
        {"from": add_recipient_factory.trustedCaller()},
    )
    motion1_id = tx.events["MotionCreated"]["_motionId"]
    motion1_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    tx = easy_track.createMotion(
        add_recipient_factory,
        encode_calldata("(address,string)", [recipient2, recipient2_title]),
        {"from": add_recipient_factory.trustedCaller()},
    )
    motion2_id = tx.events["MotionCreated"]["_motionId"]
    motion2_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    # Enact in reverse order just to check that order in the registry
    # depends on the order of motions enactment but order of creation
    easy_track.enactMotion(motion2_id, motion2_calldata, {"from": easy_track})
    easy_track.enactMotion(motion1_id, motion1_calldata, {"from": easy_track})

    assert allowed_recipients_registry.isRecipientAllowed(recipient1)
    assert allowed_recipients_registry.isRecipientAllowed(recipient2)
    assert allowed_recipients_registry.getAllowedRecipients() == [recipient2, recipient1]


def test_fail_if_add_same_recipient_twice(entire_allowed_recipients_setup, accounts):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        _,  # top_up_factory,
        add_recipient_factory,
        _,  # remove_recipient_factory,
    ) = entire_allowed_recipients_setup

    recipient = accounts[8]
    recipient_title = "New Allowed Recipient"

    add_recipient_by_motion(recipient, recipient_title, easy_track, add_recipient_factory)

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        add_recipient_by_motion(recipient, recipient_title, easy_track, add_recipient_factory)


def test_remove_recipient_motion(entire_allowed_recipients_setup, accounts):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        _,  # top_up_factory,
        add_recipient_factory,
        remove_recipient_factory,
    ) = entire_allowed_recipients_setup

    recipient = accounts[8]
    recipient_title = "New Allowed Recipient"

    add_recipient_by_motion(recipient, recipient_title, easy_track, add_recipient_factory)
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 1

    call_data = encode_single("(address)", [recipient.address])
    assert remove_recipient_factory.decodeEVMScriptCallData(call_data) == recipient.address

    tx = easy_track.createMotion(
        remove_recipient_factory,
        call_data,
        {"from": remove_recipient_factory.trustedCaller()},
    )

    assert tx.events["MotionCreated"]["_evmScriptCallData"] == "0x" + call_data.hex()

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    tx = easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        call_data,
        {"from": recipient},
    )
    assert_event_exists(
        tx,
        "RecipientRemoved",
        {"_recipient": recipient},
    )
    assert not allowed_recipients_registry.isRecipientAllowed(recipient)
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 0


def test_fail_remove_recipient_if_empty_allowed_recipients_list(
    entire_allowed_recipients_setup, accounts
):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        _,  # top_up_factory,
        _,  # add_recipient_factory,
        remove_recipient_factory,
    ) = entire_allowed_recipients_setup

    recipient = accounts[8]
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 0

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_recipient_by_motion(
            recipient, easy_track, remove_recipient_factory, allowed_recipients_registry
        )


def test_fail_remove_recipient_if_it_is_not_allowed(
    entire_allowed_recipients_setup, accounts, stranger
):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        _,  # top_up_factory,
        add_recipient_factory,
        remove_recipient_factory,
    ) = entire_allowed_recipients_setup

    add_recipient_by_motion(accounts[8], "Allowed Recipient", easy_track, add_recipient_factory)

    assert len(allowed_recipients_registry.getAllowedRecipients()) > 0
    assert not allowed_recipients_registry.isRecipientAllowed(stranger)

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_recipient_by_motion(
            stranger, easy_track, remove_recipient_factory, allowed_recipients_registry
        )


def test_fail_if_second_top_up_in_the_period_exceeds_limit(
    entire_allowed_recipients_setup_with_two_recipients,
    agent,
):
    """Revert 2nd payout which together with 1st payout exceed limits in the same period"""
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        top_up_factory,
        _,  # add_recipient_factory,
        _,  # remove_recipient_factory,
        recipient1,
        recipient2,
    ) = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, 6
    set_limit_parameters_by_aragon_voting(
        period_limit, period_duration, allowed_recipients_registry, agent
    )

    recipients = list(map(lambda x: x.address, [recipient1, recipient2]))
    do_payout_to_allowed_recipients_by_motion(
        recipients, [int(3e18), int(90e18)], easy_track, top_up_factory
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        do_payout_to_allowed_recipients_by_motion(
            recipients, [int(5e18), int(4e18)], easy_track, top_up_factory
        )


def test_limit_is_renewed_in_next_period(
    entire_allowed_recipients_setup_with_two_recipients, agent
):
    """Check limit is renewed in the next period"""
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        top_up_factory,
        _,  # add_recipient_factory,
        _,  # remove_recipient_factory,
        recipient1,
        recipient2,
    ) = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, 1
    set_limit_parameters_by_aragon_voting(
        period_limit, period_duration, allowed_recipients_registry, agent
    )

    recipients = list(map(lambda x: x.address, [recipient1, recipient2]))
    do_payout_to_allowed_recipients_by_motion(
        recipients, [int(3e18), int(90e18)], easy_track, top_up_factory
    )

    chain.sleep(period_duration * MAX_SECONDS_IN_MONTH)

    second_payout = [int(5e18), int(4e18)]
    do_payout_to_allowed_recipients_by_motion(recipients, second_payout, easy_track, top_up_factory)
    assert allowed_recipients_registry.getPeriodState()[0] == sum(second_payout)


def test_both_motions_enacted_next_period_second_exceeds_limit(
    entire_allowed_recipients_setup_with_two_recipients, agent
):
    """
    Two motion created this period, the first enacted next period, the second
    is reverted due to the limit in the second period
    """
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        top_up_factory,
        _,  # add_recipient_factory,
        _,  # remove_recipient_factory,
        recipient1,
        recipient2,
    ) = entire_allowed_recipients_setup_with_two_recipients
    recipients = [recipient1.address, recipient2.address]

    period_limit, period_duration = 100 * 10**18, 1
    set_limit_parameters_by_aragon_voting(
        period_limit, period_duration, allowed_recipients_registry, agent
    )

    payout1 = [int(40e18), int(30e18)]
    payout2 = [int(30e18), int(20e18)]
    motion1_id, motion1_calldata = create_top_up_motion(
        recipients, payout1, easy_track, top_up_factory
    )
    motion2_id, motion2_calldata = create_top_up_motion(
        recipients, payout2, easy_track, top_up_factory
    )

    chain.sleep(period_duration * MAX_SECONDS_IN_MONTH)

    easy_track.enactMotion(motion1_id, motion1_calldata, {"from": recipient1})

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        easy_track.enactMotion(motion2_id, motion2_calldata, {"from": recipient1})


def test_fail_create_top_up_motion_if_exceeds_limit(
    entire_allowed_recipients_setup_with_two_recipients, agent
):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        top_up_factory,
        _,  # add_recipient_factory,
        _,  # remove_recipient_factory,
        recipient1,
        _,  # recipient2,
    ) = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, 1
    set_limit_parameters_by_aragon_voting(
        period_limit, period_duration, allowed_recipients_registry, agent
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_top_up_motion([recipient1.address], [period_limit + 1], easy_track, top_up_factory)


def test_fail_top_up_if_limit_decreased_while_motion_is_in_flight(
    entire_allowed_recipients_setup_with_two_recipients, agent
):
    (
        easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        top_up_factory,
        _,  # add_recipient_factory,
        _,  # remove_recipient_factory,
        recipient1,
        _,  # recipient2,
    ) = entire_allowed_recipients_setup_with_two_recipients

    period_limit, period_duration = 100 * 10**18, 1
    set_limit_parameters_by_aragon_voting(
        period_limit, period_duration, allowed_recipients_registry, agent
    )

    motion_id, motion_calldata = create_top_up_motion(
        [recipient1.address], [period_limit], easy_track, top_up_factory
    )

    set_limit_parameters_by_aragon_voting(
        period_limit // 2, period_duration, allowed_recipients_registry, agent
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        easy_track.enactMotion(
            motion_id,
            motion_calldata,
            {"from": recipient1},
        )
