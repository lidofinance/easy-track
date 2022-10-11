import pytest
from datetime import datetime

from brownie.network import chain
from brownie import accounts, reverts, ZERO_ADDRESS


from utils.evm_script import encode_call_script

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

from utils.config import get_network_name

from utils.lido import create_voting, execute_voting


MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60
RECIPIENT_TITLE = "New Allowed Recipient"


def test_registry_initial_state(
    AllowedRecipientsRegistry, accounts, owner, bokkyPooBahsDateTimeContract
):
    add_recipient_role_holder = accounts[6]
    remove_recipient_role_holder = accounts[7]
    set_limits_role_holder = accounts[8]
    update_spent_role_holder = accounts[9]

    registry = owner.deploy(
        AllowedRecipientsRegistry,
        owner,
        [add_recipient_role_holder],
        [remove_recipient_role_holder],
        [set_limits_role_holder],
        [update_spent_role_holder],
        bokkyPooBahsDateTimeContract,
    )

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, add_recipient_role_holder)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, remove_recipient_role_holder)
    assert registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, set_limits_role_holder)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, update_spent_role_holder)
    assert registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), owner)

    for role_holder in [
        add_recipient_role_holder,
        remove_recipient_role_holder,
        set_limits_role_holder,
        update_spent_role_holder,
    ]:
        assert not registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), role_holder)

    assert registry.spendableBalance() == 0
    assert registry.getLimitParameters() == (0, 0)
    with reverts():
        registry.getPeriodState()

    assert len(registry.getAllowedRecipients()) == 0


def test_registry_zero_admin_allowed(
    AllowedRecipientsRegistry, accounts, owner, bokkyPooBahsDateTimeContract
):
    """Checking no revert"""
    owner.deploy(
        AllowedRecipientsRegistry,
        ZERO_ADDRESS,
        [owner],
        [owner],
        [owner],
        [owner],
        bokkyPooBahsDateTimeContract,
    )


def test_registry_none_role_holders_allowed(
    AllowedRecipientsRegistry, accounts, owner, bokkyPooBahsDateTimeContract
):
    """Checking no revert"""
    owner.deploy(
        AllowedRecipientsRegistry,
        owner,
        [],
        [],
        [],
        [],
        bokkyPooBahsDateTimeContract,
    )


def test_registry_zero_booky_poo_bahs_data_time_address_allowed(
    AllowedRecipientsRegistry, accounts, owner, bokkyPooBahsDateTimeContract
):
    """Checking no revert"""
    owner.deploy(
        AllowedRecipientsRegistry,
        owner,
        [owner],
        [owner],
        [owner],
        [owner],
        ZERO_ADDRESS,
    )


def test_set_limit_parameters_happy_path(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1
    now = datetime.now()
    period_start = get_month_start_timestamp(now)

    tx = limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )
    assert_event_exists(tx, "CurrentPeriodAdvanced", {"_periodStartTimestamp": period_start})
    assert_event_exists(
        tx,
        "LimitsParametersChanged",
        {"_limit": period_limit, "_periodDurationMonths": period_duration},
    )
    assert len(tx.events) == 2, f"must exist two events"

    assert limits_checker.getLimitParameters() == (period_limit, period_duration)
    assert limits_checker.isUnderSpendableBalance(period_limit, 0)


def test_set_limit_parameters_by_aragon_voting(entire_allowed_recipients_setup, agent):
    # TODO: make it use only the registry (without the entire setup)
    (
        _,  # easy_track,
        _,  # evm_script_executor,
        allowed_recipients_registry,
        _,  # top_up_factory,
        _,  # add_recipient_factory,
        _,  # remove_recipient_factory,
    ) = entire_allowed_recipients_setup

    period_limit, period_duration = 100 * 10**18, 6

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


@pytest.mark.parametrize("period_duration", [1, 2, 3, 6, 12])
def test_period_range_calculation_for_all_allowed_period_durations(
    limits_checker_with_private_method_exposed, period_duration
):
    (limits_checker, set_limits_role_holder, _) = limits_checker_with_private_method_exposed

    def get_period_range_from_contract():
        return limits_checker.getPeriodState()[2:]

    def calc_period_range(period_months):
        now = datetime.now()
        first_month = limits_checker.getFirstMonthInPeriodFromCurrentMonth(now.month)
        first_month_date = now.replace(month=first_month)
        next_period_date = get_date_in_next_period(first_month_date, period_months)

        return (
            get_month_start_timestamp(first_month_date),
            get_month_start_timestamp(next_period_date),
        )

    period_limit = 0
    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )
    assert get_period_range_from_contract() == calc_period_range(
        period_duration
    ), f"incorrect range for period {period_duration}"


@pytest.mark.parametrize("period_duration", [0, 4, 5, 7, 8, 9, 10, 11, 13, 14, 100500])
def test_fail_if_set_incorrect_period_durations(limits_checker, period_duration):
    (limits_checker, set_limits_role_holder, _) = limits_checker

    period_limit = 10**18
    with reverts("INVALID_PERIOD_DURATION"):
        limits_checker.setLimitParameters(
            period_limit, period_duration, {"from": set_limits_role_holder}
        )


@pytest.mark.parametrize(
    "period_duration,current_month,period_first_month",
    [
        (1, 1, 1),
        (1, 2, 2),
        (1, 3, 3),
        (1, 4, 4),
        (1, 5, 5),
        (1, 6, 6),
        (1, 7, 7),
        (1, 8, 8),
        (1, 9, 9),
        (1, 10, 10),
        (1, 11, 11),
        (1, 12, 12),
        (2, 1, 1),
        (2, 2, 1),
        (2, 3, 3),
        (2, 4, 3),
        (2, 5, 5),
        (2, 6, 5),
        (2, 7, 7),
        (2, 8, 7),
        (2, 9, 9),
        (2, 10, 9),
        (2, 11, 11),
        (2, 12, 11),
        (3, 1, 1),
        (3, 2, 1),
        (3, 3, 1),
        (3, 4, 4),
        (3, 5, 4),
        (3, 6, 4),
        (3, 7, 7),
        (3, 8, 7),
        (3, 9, 7),
        (3, 10, 10),
        (3, 11, 10),
        (3, 12, 10),
        (6, 1, 1),
        (6, 2, 1),
        (6, 3, 1),
        (6, 4, 1),
        (6, 5, 1),
        (6, 6, 1),
        (6, 7, 7),
        (6, 8, 7),
        (6, 9, 7),
        (6, 10, 7),
        (6, 11, 7),
        (6, 12, 7),
        (12, 1, 1),
        (12, 2, 1),
        (12, 3, 1),
        (12, 4, 1),
        (12, 5, 1),
        (12, 6, 1),
        (12, 7, 1),
        (12, 8, 1),
        (12, 9, 1),
        (12, 10, 1),
        (12, 11, 1),
        (12, 12, 1),
    ],
)
def test_get_first_month_in_period_for_all_allowed_period_durations(
    limits_checker_with_private_method_exposed,
    period_duration,
    current_month,
    period_first_month,
):
    (limits_checker, set_limits_role_holder, _) = limits_checker_with_private_method_exposed

    period_limit = 0
    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    assert limits_checker.getFirstMonthInPeriodFromCurrentMonth(current_month) == period_first_month


def test_fail_if_set_limit_greater_than_max_limit(limits_checker):
    (limits_checker, set_limits_role_holder, _) = limits_checker

    period_limit, period_duration = 2**128, 1

    with reverts("TOO_LARGE_LIMIT"):
        limits_checker.setLimitParameters(
            period_limit, period_duration, {"from": set_limits_role_holder}
        )


def test_limits_checker_views_in_next_period(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker

    period_limit, period_duration = int(10e18), 1
    payout_amount = int(3e18)
    spendable_balance = period_limit - payout_amount
    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )
    limits_checker.updateSpentAmount(payout_amount, {"from": update_spent_amount_role_holder})
    assert limits_checker.spendableBalance() == spendable_balance
    assert limits_checker.getPeriodState()[:2] == (payout_amount, spendable_balance)

    chain.sleep(MAX_SECONDS_IN_MONTH * period_duration)

    assert limits_checker.spendableBalance() == spendable_balance
    assert limits_checker.getPeriodState()[:2] == (payout_amount, spendable_balance)


def test_update_spent_amount_within_the_limit(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1
    now = datetime.now()
    period_start = get_month_start_timestamp(now)
    period_end = get_month_start_timestamp(get_date_in_next_period(now, period_duration))

    tx = limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    spending = 2 * 10**18
    spendable = period_limit - spending
    tx = limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
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


def test_update_spent_amount_precisely_to_the_limit_in_multiple_portions(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1

    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    spending = 1 * 10**18
    spendable = period_limit - spending
    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.getPeriodState()[:2] == (spending, spendable)
    assert limits_checker.isUnderSpendableBalance(spendable, 0)
    assert limits_checker.isUnderSpendableBalance(
        period_limit, period_duration * MAX_SECONDS_IN_MONTH
    )

    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.getPeriodState()[:2] == (2 * spending, period_limit - 2 * spending)

    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.getPeriodState()[:2] == (period_limit, 0)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(1, {"from": update_spent_amount_role_holder})


def test_fail_if_update_spent_amount_beyond_the_limit():
    pass  # assert False, "TODO"


def test_fail_if_update_spent_amount_when_no_period_duration_set(limits_checker):
    (limits_checker, _, update_spent_amount_role_holder) = limits_checker

    with reverts("INVALID_PERIOD_DURATION"):
        limits_checker.updateSpentAmount(123, {"from": update_spent_amount_role_holder})


def test_add_recipient(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    registry.addRecipient(recipient, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient)


def test_add_recipient_with_empty_title(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    registry.addRecipient(recipient, "", {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient)


def test_add_recipient_with_zero_address(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry

    registry.addRecipient(ZERO_ADDRESS, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(ZERO_ADDRESS)


def test_add_multiple_recipients(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient1 = accounts[8].address
    recipient2 = accounts[9].address

    registry.addRecipient(recipient1, RECIPIENT_TITLE, {"from": add_recipient_role_holder})
    registry.addRecipient(recipient2, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient1)
    assert registry.isRecipientAllowed(recipient2)


def test_fail_if_add_the_same_recipient(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    registry.addRecipient(recipient, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient)
    with reverts("RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST"):
        registry.addRecipient(recipient, RECIPIENT_TITLE, {"from": add_recipient_role_holder})


def test_remove_recipient(allowed_recipients_registry):
    (
        registry,
        _,
        add_recipient_role_holder,
        remove_recipient_role_holder,
        _,
        _,
    ) = allowed_recipients_registry
    recipient = accounts[8].address

    registry.addRecipient(recipient, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient)

    registry.removeRecipient(recipient, {"from": remove_recipient_role_holder})

    assert False == registry.isRecipientAllowed(recipient)


def test_fail_if_remove_recipient_from_empty_allowed_list(allowed_recipients_registry):
    (registry, _, _, remove_recipient_role_holder, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    assert 0 == len(registry.getAllowedRecipients())
    assert False == registry.isRecipientAllowed(recipient)

    with reverts("RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeRecipient(recipient, {"from": remove_recipient_role_holder})


def test_fail_if_remove_not_allowed_recipient(allowed_recipients_registry):
    (
        registry,
        _,
        add_recipient_role_holder,
        remove_recipient_role_holder,
        _,
        _,
    ) = allowed_recipients_registry
    recipient1 = accounts[8].address
    recipient2 = accounts[9].address

    registry.addRecipient(recipient1, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient1)

    with reverts("RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeRecipient(recipient2, {"from": remove_recipient_role_holder})


def test_access_stranger_cannot_set_limit_parameters(limits_checker, stranger):
    (limits_checker, _, _) = limits_checker

    with reverts(access_revert_message(stranger, SET_LIMIT_PARAMETERS_ROLE)):
        limits_checker.setLimitParameters(123, 1, {"from": stranger})


def test_access_stranger_cannot_update_spent_amount(limits_checker, stranger):
    (limits_checker, _, _) = limits_checker

    with reverts(access_revert_message(stranger, UPDATE_SPENT_AMOUNT_ROLE)):
        limits_checker.updateSpentAmount(123, {"from": stranger})


def test_rights_are_not_shared_by_different_roles(
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
