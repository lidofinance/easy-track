import datetime

from brownie.network import chain
from brownie import EasyTrack, EVMScriptExecutor, accounts, reverts
from typing import List

from eth_abi import encode_single
from utils.evm_script import encode_call_script, encode_calldata

from utils.config import get_network_name

from utils.lido import create_voting, execute_voting, addresses

from utils.test_helpers import (
    assert_single_event,
    assert_event_exists,
    access_control_revert_message,
    SET_LIMIT_PARAMETERS_ROLE,
    UPDATE_LIMIT_SPENDINGS_ROLE,
)

from utils.deployment import attach_evm_script_allowed_recipients_factories

import constants


MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60


# #######################################
#   The following TODOs are test plan   #
# #######################################

# TODO: just motion creation for the new factory

# TODO: test motion ended and enacted in the same period

# TODO: test motion ended in the same and enacted in the next period

# TODO: test motion ended and enacted in the next period

# TODO: test motion enacted in after-the-next period

# TODO: test attempt to exceed the limit for a specific recipient
#       test attempt to exceed the period limit
#       test the limit is cumulative for all allowed recipients

# TODO: test max number of the allowed recipients

# TODO: test attempt to remove not allowed recipient

# TODO: test attempt to add an already allowed recipient

# TODO: ?? the limits are checked at the time of enactment

# TODO: ?? the limits are checked at the time of motion creation

# TODO: test LimitsChecker functions
#       - incorrect period durations (e. g. 7 months)
#       - cover all functions

# TODO: changing limit and/or period duration while motion is on the go

# TODO: checking that createMotion also reverts if limit exceeds

# TODO: cover all the events
#       - RecipientAddedToAllowedList
#       - RecipientRemovedFromAllowedList
#       - LimitsParametersChanged
#       - FundsSpent

# TODO: cover all error messages
#       - RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST
#       - RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST
#       - ALLOWED_RECIPIENT_ALREADY_ADDED
#       - ALLOWED_RECIPIENT_NOT_FOUND
#       - LENGTH_MISMATCH
#       - EMPTY_DATA
#       - ZERO_AMOUNT
#       - RECIPIENT_NOT_ALLOWED
#       - SUM_EXCEEDS_LIMIT
#       - WRONG_PERIOD_DURATION

# TODO: add test_xxx for each factory like tests in tests/evm_script_factories

# TODO: make the tests not dependent on the current date and proximity of now to period boundaries

# TODO: limits start, end calculation


def set_limit_parameters(period_limit, period_duration, allowed_recipients_registry, agent):
    """Do Aragon voting to set limit parameters to the allowed recipients registry"""
    set_limit_parameters_voting_id, _ = create_voting(
        evm_script=encode_call_script(
            [
                (
                    allowed_recipients_registry.address,
                    allowed_recipients_registry.setLimitParameters.encode_input(
                        period_limit,
                        period_duration,
                    ),
                ),
            ]
        ),
        description="Set limit parameters",
        network=get_network_name(),
        tx_params={"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    execute_voting(set_limit_parameters_voting_id, get_network_name())

    allowed_recipients_registry.getLimitParameters() == (period_limit, period_duration)


def create_top_up_motion(recipients: List[str], amounts: List[int], easy_track, top_up_factory):
    script_call_data = encode_single(
        "(address[],uint256[])",
        [recipients, amounts],
    )
    tx = easy_track.createMotion(
        top_up_factory,
        script_call_data,
        {"from": top_up_factory.trustedCaller()},
    )
    motion_id = tx.events["MotionCreated"]["_motionId"]
    return motion_id, script_call_data


def do_payout_to_allowed_recipients(recipients, amounts, easy_track, top_up_factory):
    motion_id, script_call_data = create_top_up_motion(
        recipients, amounts, easy_track, top_up_factory
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    easy_track.enactMotion(
        motion_id,
        script_call_data,
        {"from": recipients[0]},
    )


def test_add_remove_recipient(entire_allowed_recipients_setup, accounts, stranger):
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

    add_recipient_calldata = encode_calldata(
        "(address,string)", [recipient.address, recipient_title]
    )

    tx = easy_track.createMotion(
        add_recipient_factory,
        add_recipient_calldata,
        {"from": add_recipient_factory.trustedCaller()},
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    tx = easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert_event_exists(
        tx,
        "RecipientAddedToAllowedList",
        {"_recipient": recipient, "_title": recipient_title},
    )

    assert len(easy_track.getMotions()) == 0
    assert allowed_recipients_registry.getAllowedRecipients() == [recipient]

    assert allowed_recipients_registry.isAllowedRecipient(recipient)
    assert not allowed_recipients_registry.isAllowedRecipient(stranger)

    # create new motion to remove a allowed recipient
    tx = easy_track.createMotion(
        remove_recipient_factory,
        encode_single("(address)", [recipient.address]),
        {"from": remove_recipient_factory.trustedCaller()},
    )
    motion_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    tx = easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        motion_calldata,
        {"from": stranger},
    )
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 0
    assert_event_exists(
        tx,
        "RecipientRemovedFromAllowedList",
        {"_recipient": recipient},
    )
    assert not allowed_recipients_registry.isAllowedRecipient(recipient)


def test_motion_created_and_enacted_in_same_period(
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

    period_limit, period_duration = 100 * 10**18, 1
    set_limit_parameters(period_limit, period_duration, allowed_recipients_registry, agent)

    recipients = list(map(lambda x: x.address, [recipient1, recipient2]))
    do_payout_to_allowed_recipients(
        recipients, [int(3e18), int(90e18)], easy_track, top_up_factory
    )

    with reverts("SUM_EXCEEDS_LIMIT"):
        do_payout_to_allowed_recipients(
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
    set_limit_parameters(period_limit, period_duration, allowed_recipients_registry, agent)

    recipients = list(map(lambda x: x.address, [recipient1, recipient2]))
    do_payout_to_allowed_recipients(
        recipients, [int(3e18), int(90e18)], easy_track, top_up_factory
    )

    chain.sleep(period_duration * MAX_SECONDS_IN_MONTH)

    second_payout = [int(5e18), int(4e18)]
    do_payout_to_allowed_recipients(
        recipients, second_payout, easy_track, top_up_factory
    )
    assert allowed_recipients_registry.getCurrentPeriodState()[0] == sum(second_payout)


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
    set_limit_parameters(period_limit, period_duration, allowed_recipients_registry, agent)

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

    with reverts("SUM_EXCEEDS_LIMIT"):
        easy_track.enactMotion(motion2_id, motion2_calldata, {"from": recipient1})


def test_limits_checker_access_restriction(
    owner, lego_program, stranger, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    manager = lego_program
    script_executor = easy_track.evmScriptExecutor()

    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [manager], [script_executor], bokkyPooBahsDateTimeContract
    )

    with reverts(access_control_revert_message(stranger, SET_LIMIT_PARAMETERS_ROLE)):
        limits_checker.setLimitParameters(123, 1, {"from": stranger})

    with reverts(access_control_revert_message(owner, SET_LIMIT_PARAMETERS_ROLE)):
        limits_checker.setLimitParameters(123, 1, {"from": owner})

    with reverts(access_control_revert_message(stranger, UPDATE_LIMIT_SPENDINGS_ROLE)):
        limits_checker.updateSpendableBalance(123, {"from": stranger})

    with reverts(access_control_revert_message(manager, UPDATE_LIMIT_SPENDINGS_ROLE)):
        limits_checker.updateSpendableBalance(123, {"from": manager})


def test_limits_checker_update_balance_with_zero_periodDuration(
    owner, lego_program, stranger, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    manager = lego_program
    script_executor = easy_track.evmScriptExecutor()

    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [manager], [script_executor], bokkyPooBahsDateTimeContract
    )

    with reverts("WRONG_PERIOD_DURATION"):
        limits_checker.updateSpendableBalance(123, {"from": script_executor})


def test_limits_checker_incorrect_period_duration(
    owner, lego_program, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    manager = lego_program
    script_executor = easy_track.evmScriptExecutor()

    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [manager], [script_executor], bokkyPooBahsDateTimeContract
    )

    period_limit = 10**18
    for duration in [0, 4, 5, 7, 8, 9, 10, 11, 13, 14, 100500]:
        with reverts("WRONG_PERIOD_DURATION"):
            limits_checker.setLimitParameters(period_limit, duration, {"from": manager})


def calc_period_range_timestamps(now_timestamp, period_duration_months):
    now = datetime.datetime.fromtimestamp(now_timestamp)
    now.date()
    pass


def test_limits_checker_period_ranges(
    owner, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    script_executor = easy_track.evmScriptExecutor()
    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [owner], [script_executor], bokkyPooBahsDateTimeContract
    )

    period_limit, period_duration = 0, 3
    limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
    (_, _, start, end) = limits_checker.getCurrentPeriodState()
    print(
        f"start={start}, {datetime.datetime.fromtimestamp(start).isoformat()},\nend={end}, {datetime.datetime.fromtimestamp(end).isoformat()}"
    )


def test_limits_checker_get_first_month_in_period(
    owner, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    script_executor = easy_track.evmScriptExecutor()
    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [owner], [script_executor], bokkyPooBahsDateTimeContract
    )

    period_limit, period_duration = 0, 1
    limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
    for i in range(1, 13):
        assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(i) == i

    period_duration = 2
    limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(1) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(2) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(3) == 3
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(4) == 3
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(5) == 5
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(6) == 5
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(7) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(8) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(9) == 9
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(10) == 9
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(11) == 11
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(12) == 11

    period_duration = 3
    limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(1) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(2) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(3) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(4) == 4
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(5) == 4
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(6) == 4
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(7) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(8) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(9) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(10) == 10
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(11) == 10
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(12) == 10

    period_duration = 6
    limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(1) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(2) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(3) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(4) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(5) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(6) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(7) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(8) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(9) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(10) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(11) == 7
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(12) == 7

    period_duration = 12
    limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(1) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(2) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(3) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(4) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(5) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(6) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(7) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(8) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(9) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(10) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(11) == 1
    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(12) == 1


def test_limits_checker_general(
    owner, lego_program, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    # TODO: don't fix specific months, otherwise the test won't work next month
    SEPTEMBER_1 = 1661990400  # Sep 01 2022 00:00:00 GMT+0000
    OCTOBER_1 = 1664582400  # Oct 01 2022 00:00:00 GMT+0000
    period_start = SEPTEMBER_1
    period_end = OCTOBER_1

    manager = lego_program
    script_executor = easy_track.evmScriptExecutor()

    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [manager], [script_executor], bokkyPooBahsDateTimeContract
    )
    assert limits_checker.getLimitParameters() == (0, 0)

    # TODO fix: call reverts due to call of _getPeriodStartFromTimestamp when period duration is zero
    # assert limits_checker.getCurrentPeriodState() == (0, 0, 0, 0)

    assert limits_checker.currentSpendableBalance() == 0
    assert limits_checker.isUnderSpendableBalance(0, easy_track.motionDuration())

    period_limit, period_duration = 3 * 10**18, 1

    tx = limits_checker.setLimitParameters(period_limit, period_duration, {"from": manager})
    assert_single_event(
        tx,
        "LimitsParametersChanged",
        {"_limit": period_limit, "_periodDurationMonth": period_duration},
    )
    assert limits_checker.getLimitParameters() == (period_limit, period_duration)

    spending = 1 * 10**18
    spendable = period_limit - spending
    tx = limits_checker.updateSpendableBalance(spending, {"from": script_executor})
    assert limits_checker.getCurrentPeriodState() == (spending, spendable, period_start, period_end)
    assert_single_event(
        tx,
        "FundsSpent",
        {
            "_alreadySpentAmount": spending,
            "_spendableAmount": spendable,
            "_periodStartTimestamp": period_start,
            "_periodEndTimestamp": period_end,
        },
    )

    limits_checker.updateSpendableBalance(spending, {"from": script_executor})
    assert limits_checker.getCurrentPeriodState() == (
        2 * spending,
        period_limit - 2 * spending,
        period_start,
        period_end,
    )

    limits_checker.updateSpendableBalance(spending, {"from": script_executor})
    assert limits_checker.getCurrentPeriodState() == (
        period_limit,
        0,
        period_start,
        period_end,
    )

    with reverts("SUM_EXCEEDS_LIMIT"):
        limits_checker.updateSpendableBalance(1, {"from": script_executor})
