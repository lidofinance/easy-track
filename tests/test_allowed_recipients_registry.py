from datetime import datetime

from brownie.network import chain
from brownie import accounts, reverts
from typing import List

from eth_abi import encode_single
from utils.evm_script import encode_call_script, encode_calldata

from utils.config import get_network_name

from utils.lido import create_voting, execute_voting

from utils.test_helpers import (
    assert_single_event,
    assert_event_exists,
    access_revert_message,
    get_month_start_timestamp,
    get_date_in_next_period,
    SET_LIMIT_PARAMETERS_ROLE,
    UPDATE_SPENT_AMOUNT_ROLE,
    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
)

import constants


MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60


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

    assert allowed_recipients_registry.getLimitParameters() == (period_limit, period_duration)


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


def add_recipient(
    recipient, recipient_title, easy_track, add_recipient_factory, allowed_recipients_registry
):
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


def remove_recipient(recipient, easy_track, remove_recipient_factory, allowed_recipients_registry):
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


def test_add_remove_recipients_directly_via_registry(
    AllowedRecipientsRegistry, owner, voting, accounts, bokkyPooBahsDateTimeContract
):
    deployer = owner
    manager = accounts[7]
    registry = deployer.deploy(
        AllowedRecipientsRegistry,
        voting,
        [manager],
        [manager],
        [manager],
        [manager],
        bokkyPooBahsDateTimeContract,
    )
    recipient = accounts[8].address
    recipient_title = "New Allowed Recipient"

    with reverts(access_revert_message(deployer, ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE)):
        registry.addRecipient(recipient, recipient_title, {"from": deployer})

    registry.addRecipient(recipient, recipient_title, {"from": manager})
    assert registry.getAllowedRecipients() == [recipient]

    with reverts("RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST"):
        registry.addRecipient(recipient, recipient_title, {"from": manager})

    with reverts(access_revert_message(deployer, REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE)):
        registry.removeRecipient(recipient, {"from": deployer})

    registry.removeRecipient(recipient, {"from": manager})
    assert registry.getAllowedRecipients() == []

    with reverts("RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeRecipient(recipient, {"from": manager})


def test_limits_checker_views_in_next_period(
    owner, LimitsCheckerWrapper, bokkyPooBahsDateTimeContract
):
    """amountSpent and spendableBalance"""
    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [owner], [owner], bokkyPooBahsDateTimeContract
    )

    period_limit, period_duration = int(10e18), 1
    payout_amount = int(3e18)
    spendable_balance = period_limit - payout_amount
    limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
    limits_checker.updateSpentAmount(payout_amount, {"from": owner})
    assert limits_checker.spendableBalance() == spendable_balance
    assert limits_checker.getPeriodState()[:2] == (payout_amount, spendable_balance)

    chain.sleep(MAX_SECONDS_IN_MONTH * period_duration)

    assert limits_checker.spendableBalance() == spendable_balance
    assert limits_checker.getPeriodState()[:2] == (payout_amount, spendable_balance)


def test_allowed_recipients_registry_roles(
    AllowedRecipientsRegistry, owner, voting, accounts, bokkyPooBahsDateTimeContract
):
    deployer = owner
    add_role_holder = accounts[6]
    remove_role_holder = accounts[7]
    set_limit_role_holder = accounts[8]
    update_limit_role_holder = accounts[9]

    registry = deployer.deploy(
        AllowedRecipientsRegistry,
        voting,
        [add_role_holder],
        [remove_role_holder],
        [set_limit_role_holder],
        [update_limit_role_holder],
        bokkyPooBahsDateTimeContract,
    )
    assert registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), voting)

    recipient = accounts[8].address
    recipient_title = "New Allowed Recipient"

    for caller in [deployer, remove_role_holder, set_limit_role_holder, update_limit_role_holder]:
        with reverts(access_revert_message(caller, ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE)):
            registry.addRecipient(recipient, recipient_title, {"from": caller})

    for caller in [deployer, add_role_holder, set_limit_role_holder, update_limit_role_holder]:
        with reverts(access_revert_message(caller, REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE)):
            registry.removeRecipient(recipient, {"from": caller})

    for caller in [deployer, add_role_holder, remove_role_holder, update_limit_role_holder]:
        with reverts(access_revert_message(caller, SET_LIMIT_PARAMETERS_ROLE)):
            registry.setLimitParameters(0, 1, {"from": caller})

    for caller in [deployer, add_role_holder, remove_role_holder, set_limit_role_holder]:
        with reverts(access_revert_message(caller, UPDATE_SPENT_AMOUNT_ROLE)):
            registry.updateSpentAmount(1, {"from": caller})


def test_limits_checker_access_restriction(
    owner, lego_program, stranger, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    manager = lego_program
    script_executor = easy_track.evmScriptExecutor()

    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [manager], [script_executor], bokkyPooBahsDateTimeContract
    )

    with reverts(access_revert_message(stranger, SET_LIMIT_PARAMETERS_ROLE)):
        limits_checker.setLimitParameters(123, 1, {"from": stranger})

    with reverts(access_revert_message(owner, SET_LIMIT_PARAMETERS_ROLE)):
        limits_checker.setLimitParameters(123, 1, {"from": owner})

    with reverts(access_revert_message(stranger, UPDATE_SPENT_AMOUNT_ROLE)):
        limits_checker.updateSpentAmount(123, {"from": stranger})

    with reverts(access_revert_message(manager, UPDATE_SPENT_AMOUNT_ROLE)):
        limits_checker.updateSpentAmount(123, {"from": manager})


def test_limits_checker_update_balance_with_zero_periodDuration(
    owner, lego_program, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    manager = lego_program
    script_executor = easy_track.evmScriptExecutor()

    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [manager], [script_executor], bokkyPooBahsDateTimeContract
    )

    with reverts("INVALID_PERIOD_DURATION"):
        limits_checker.updateSpentAmount(123, {"from": script_executor})


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
        with reverts("INVALID_PERIOD_DURATION"):
            limits_checker.setLimitParameters(period_limit, duration, {"from": manager})


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


def test_limits_checker_period_range(
    owner, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    script_executor = easy_track.evmScriptExecutor()
    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [owner], [script_executor], bokkyPooBahsDateTimeContract
    )

    def get_period_range_from_contract():
        return limits_checker.getPeriodState()[2:]

    def calc_period_range(period_months):
        first_month = limits_checker.getFirstMonthInPeriodFromCurrentMonth(datetime.now().month)
        first_month_date = datetime.now().replace(month=first_month)
        next_period_date = get_date_in_next_period(first_month_date, period_months)

        return (
            get_month_start_timestamp(first_month_date),
            get_month_start_timestamp(next_period_date),
        )

    period_limit, period_duration = 0, 1

    for period_duration in [1, 2, 3, 6, 12]:
        limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})
        assert get_period_range_from_contract() == calc_period_range(
            period_duration
        ), f"incorrect range for period {period_duration}"


def test_limits_checker_too_large_limit(
    owner, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    script_executor = easy_track.evmScriptExecutor()
    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [owner], [script_executor], bokkyPooBahsDateTimeContract
    )

    period_limit, period_duration = 2 ** 128, 1

    with reverts("TOO_LARGE_LIMIT"):
        limits_checker.setLimitParameters(period_limit, period_duration, {"from": owner})



def test_limits_checker_general(
    owner, lego_program, LimitsCheckerWrapper, easy_track, bokkyPooBahsDateTimeContract
):
    manager = lego_program
    script_executor = easy_track.evmScriptExecutor()

    limits_checker = owner.deploy(
        LimitsCheckerWrapper, [manager], [script_executor], bokkyPooBahsDateTimeContract
    )
    assert limits_checker.getLimitParameters() == (0, 0)
    assert not limits_checker.hasRole(limits_checker.DEFAULT_ADMIN_ROLE(), manager)
    assert not limits_checker.hasRole(limits_checker.DEFAULT_ADMIN_ROLE(), script_executor)

    with reverts():
        limits_checker.getPeriodState()

    assert limits_checker.spendableBalance() == 0
    assert limits_checker.isUnderSpendableBalance(0, easy_track.motionDuration())

    period_limit, period_duration = 3 * 10**18, 1
    period_start = get_month_start_timestamp(datetime.now())
    period_end = get_month_start_timestamp(get_date_in_next_period(datetime.now(), period_duration))

    tx = limits_checker.setLimitParameters(period_limit, period_duration, {"from": manager})
    assert_event_exists(tx, "CurrentPeriodAdvanced", {"_periodStartTimestamp": period_start})
    assert_event_exists(tx, "LimitsParametersChanged", {"_limit": period_limit, "_periodDurationMonths": period_duration})
    assert len(tx.events) == 2, f"must exist two events"

    assert limits_checker.getLimitParameters() == (period_limit, period_duration)
    assert limits_checker.isUnderSpendableBalance(period_limit, 0)

    spending = 1 * 10**18
    spendable = period_limit - spending
    tx = limits_checker.updateSpentAmount(spending, {"from": script_executor})
    assert limits_checker.getPeriodState() == (spending, spendable, period_start, period_end)
    assert limits_checker.isUnderSpendableBalance(spendable, 0)
    assert limits_checker.isUnderSpendableBalance(
        period_limit, period_duration * MAX_SECONDS_IN_MONTH
    )
    assert_single_event(
        tx,
        "SpendableAmountChanged",
        {
            "_alreadySpentAmount": spending,
            "_spendableBalance": spendable,
            "_periodStartTimestamp": period_start,
            "_periodEndTimestamp": period_end,
        },
    )

    limits_checker.updateSpentAmount(spending, {"from": script_executor})
    assert limits_checker.getPeriodState() == (
        2 * spending,
        period_limit - 2 * spending,
        period_start,
        period_end,
    )

    limits_checker.updateSpentAmount(spending, {"from": script_executor})
    assert limits_checker.getPeriodState() == (
        period_limit,
        0,
        period_start,
        period_end,
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(1, {"from": script_executor})
