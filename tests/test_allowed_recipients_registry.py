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
    calc_period_first_month,
    calc_period_range,
    advance_chain_time_to_beginning_of_the_next_period,
    SET_LIMIT_PARAMETERS_ROLE,
    UPDATE_SPENT_AMOUNT_ROLE,
    ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE,
    REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE,
)

from utils.config import get_network_name

from utils.lido import create_voting, execute_voting


MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60
RECIPIENT_TITLE = "New Allowed Recipient"


# ------------
# constructor
# ------------


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

    assert registry.bokkyPooBahsDateTimeContract() == bokkyPooBahsDateTimeContract

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


# ------------
# access control
# ------------


def test_rights_are_not_shared_by_different_roles(
    AllowedRecipientsRegistry, owner, stranger, voting, accounts, bokkyPooBahsDateTimeContract
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

    for caller in [
        deployer,
        remove_role_holder,
        set_limit_role_holder,
        update_limit_role_holder,
        stranger,
    ]:
        with reverts(access_revert_message(caller, ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE)):
            registry.addRecipient(recipient, recipient_title, {"from": caller})

    for caller in [
        deployer,
        add_role_holder,
        set_limit_role_holder,
        update_limit_role_holder,
        stranger,
    ]:
        with reverts(access_revert_message(caller, REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE)):
            registry.removeRecipient(recipient, {"from": caller})

    for caller in [
        deployer,
        add_role_holder,
        remove_role_holder,
        update_limit_role_holder,
        stranger,
    ]:
        with reverts(access_revert_message(caller, SET_LIMIT_PARAMETERS_ROLE)):
            registry.setLimitParameters(0, 1, {"from": caller})

    for caller in [deployer, add_role_holder, remove_role_holder, set_limit_role_holder, stranger]:
        with reverts(access_revert_message(caller, UPDATE_SPENT_AMOUNT_ROLE)):
            registry.updateSpentAmount(1, {"from": caller})



def test_multiple_role_holders(
    AllowedRecipientsRegistry, owner, voting, accounts, bokkyPooBahsDateTimeContract
):
    deployer = owner
    add_role_holders = (accounts[2], accounts[3])
    remove_role_holders = (accounts[4], accounts[5])
    set_limit_role_holders = (accounts[6], accounts[7])
    update_limit_role_holders = (accounts[8], accounts[9])

    registry = deployer.deploy(
        AllowedRecipientsRegistry,
        voting,
        add_role_holders,
        remove_role_holders,
        set_limit_role_holders,
        update_limit_role_holders,
        bokkyPooBahsDateTimeContract,
    )
    recipient_title = "New Allowed Recipient"

    for caller in accounts:
        if not caller in add_role_holders:
            with reverts(access_revert_message(caller, ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE)):
                registry.addRecipient(caller, recipient_title, {"from": caller})

    for recipient in accounts[0:5]:
        registry.addRecipient(recipient, recipient_title, {"from": add_role_holders[0]})
    for recipient in accounts[5:10]:
        registry.addRecipient(recipient, recipient_title, {"from": add_role_holders[1]})

    for caller in accounts:
        if caller in remove_role_holders:
            registry.removeRecipient(caller, {"from": caller})
        else:
            with reverts(access_revert_message(caller, REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE)):
                registry.removeRecipient(caller, {"from": caller})

    for caller in accounts:
        if caller in set_limit_role_holders:
            registry.setLimitParameters(5, 1, {"from": caller})
        else:
            with reverts(access_revert_message(caller, SET_LIMIT_PARAMETERS_ROLE)):
                registry.setLimitParameters(5, 1, {"from": caller})

    for caller in accounts:
        if caller in update_limit_role_holders:
            registry.updateSpentAmount(1, {"from": caller})
        else:
            with reverts(access_revert_message(caller, UPDATE_SPENT_AMOUNT_ROLE)):
                registry.updateSpentAmount(1, {"from": caller})


def test_access_stranger_cannot_set_limit_parameters(limits_checker, stranger):
    (limits_checker, _, _) = limits_checker

    with reverts(access_revert_message(stranger, SET_LIMIT_PARAMETERS_ROLE)):
        limits_checker.setLimitParameters(123, 1, {"from": stranger})


def test_access_stranger_cannot_update_spent_amount(limits_checker, stranger):
    (limits_checker, _, _) = limits_checker

    with reverts(access_revert_message(stranger, UPDATE_SPENT_AMOUNT_ROLE)):
        limits_checker.updateSpentAmount(123, {"from": stranger})


# ------------
# AllowedRecipientsRegistry logic
# ------------


def test_add_recipient(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    registry.addRecipient(recipient, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient)
    assert len(registry.getAllowedRecipients()) == 1
    assert registry.getAllowedRecipients()[0] == recipient


def test_add_recipient_with_empty_title(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    registry.addRecipient(recipient, "", {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient)
    assert len(registry.getAllowedRecipients()) == 1
    assert registry.getAllowedRecipients()[0] == recipient


def test_add_recipient_with_zero_address(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry

    registry.addRecipient(ZERO_ADDRESS, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(ZERO_ADDRESS)
    assert len(registry.getAllowedRecipients()) == 1
    assert registry.getAllowedRecipients()[0] == ZERO_ADDRESS


def test_add_multiple_recipients(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient1 = accounts[8].address
    recipient2 = accounts[9].address

    registry.addRecipient(recipient1, RECIPIENT_TITLE, {"from": add_recipient_role_holder})
    registry.addRecipient(recipient2, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient1)
    assert registry.isRecipientAllowed(recipient2)
    assert len(registry.getAllowedRecipients()) == 2
    assert registry.getAllowedRecipients()[0] == recipient1
    assert registry.getAllowedRecipients()[1] == recipient2


def test_fail_if_add_the_same_recipient(allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    registry.addRecipient(recipient, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient)
    with reverts("RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST"):
        registry.addRecipient(recipient, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert len(registry.getAllowedRecipients()) == 1


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

    assert not registry.isRecipientAllowed(recipient)

    assert len(registry.getAllowedRecipients()) == 0


def test_remove_not_last_recipient_in_the_list(allowed_recipients_registry):
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
    registry.addRecipient(recipient2, RECIPIENT_TITLE, {"from": add_recipient_role_holder})

    assert registry.isRecipientAllowed(recipient1)
    assert registry.isRecipientAllowed(recipient2)

    registry.removeRecipient(recipient1, {"from": remove_recipient_role_holder})

    assert registry.getAllowedRecipients() == [recipient2]


def test_fail_if_remove_recipient_from_empty_allowed_list(allowed_recipients_registry):
    (registry, _, _, remove_recipient_role_holder, _, _) = allowed_recipients_registry
    recipient = accounts[8].address

    assert 0 == len(registry.getAllowedRecipients())
    assert not registry.isRecipientAllowed(recipient)

    with reverts("RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeRecipient(recipient, {"from": remove_recipient_role_holder})

    assert len(registry.getAllowedRecipients()) == 0


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

    assert len(registry.getAllowedRecipients()) == 1
    assert registry.getAllowedRecipients()[0] == recipient1
    assert registry.isRecipientAllowed(recipient1)
    assert not registry.isRecipientAllowed(recipient2)


# ------------
# LimitsChecker logic
# ------------


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


def test_period_range_calculation_for_all_allowed_period_durations(
    limits_checker_with_private_method_exposed,
):
    (limits_checker, set_limits_role_holder, _) = limits_checker_with_private_method_exposed

    assert limits_checker.getLimitParameters()[1] == 0

    period_limit = 0

    # duration is iterated inside the test instead of test parametrization
    # to check that period range is calculated correctly even if the contract
    # state wasn't the initial state
    for _ in range(12):
        for duration in [1, 2, 3, 6, 12]:
            limits_checker.setLimitParameters(
                period_limit, duration, {"from": set_limits_role_holder}
            )
            _, _, period_start, period_end = limits_checker.getPeriodState()
            assert (period_start, period_end) == calc_period_range(
                duration, chain.time()
            ), f"incorrect range for period {duration}"

        chain.sleep(MAX_SECONDS_IN_MONTH)


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
    [(1, i, calc_period_first_month(1, i)) for i in range(1, 13)]
    + [(2, i, calc_period_first_month(2, i)) for i in range(1, 13)]
    + [(3, i, calc_period_first_month(3, i)) for i in range(1, 13)]
    + [(6, i, calc_period_first_month(6, i)) for i in range(1, 13)]
    + [(12, i, calc_period_first_month(12, i)) for i in range(1, 13)],
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
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == payout_amount
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == spendable_balance

    chain.sleep(MAX_SECONDS_IN_MONTH * period_duration)

    assert limits_checker.spendableBalance() == spendable_balance
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == payout_amount
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == spendable_balance


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
    assert limits_checker.spendableBalance() == spendable
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == spendable
    assert limits_checker.isUnderSpendableBalance(spendable, 0)
    assert limits_checker.isUnderSpendableBalance(
        period_limit, period_duration * MAX_SECONDS_IN_MONTH
    )

    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == 2 * spending
    assert (
        limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == period_limit - 2 * spending
    )

    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == period_limit
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == 0

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(1, {"from": update_spent_amount_role_holder})


def test_spending_amount_is_restored_in_the_next_period(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1
    spending = 3 * 10**18
    spendable = period_limit - spending

    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.spendableBalance() == spendable

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})

    chain.sleep(MAX_SECONDS_IN_MONTH * period_duration)

    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.spendableBalance() == spendable


def test_fail_if_update_spent_amount_beyond_the_limit(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1
    spending = 5 * 10**18

    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    (_, spendable_balance, _, _) = limits_checker.getPeriodState()

    assert spendable_balance == (period_limit)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})


def test_spendable_amount_if_limit_increased(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1

    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    spending = 1 * 10**18
    spendable = period_limit - spending
    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.spendableBalance() == spendable
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == spendable

    new_period_limit = 2 * period_limit
    new_spendable = spendable + (new_period_limit - period_limit)
    limits_checker.setLimitParameters(
        new_period_limit, period_duration, {"from": set_limits_role_holder}
    )
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == new_spendable
    assert limits_checker.spendableBalance() == new_spendable


def test_spendable_amount_if_limit_decreased_below_spent_amount(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1

    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    spending = 1 * 10**18
    spendable = period_limit - spending
    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.spendableBalance() == spendable
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == spendable

    new_period_limit = spending // 2
    new_spendable = 0
    # NB!: already spent amount decreased to the new limit
    new_spending = new_period_limit
    limits_checker.setLimitParameters(
        new_period_limit, period_duration, {"from": set_limits_role_holder}
    )
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == new_spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == new_spendable
    assert limits_checker.spendableBalance() == new_spendable


def test_spendable_amount_if_limit_decreased_not_below_spent_amount(limits_checker):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit, period_duration = 3 * 10**18, 1

    limits_checker.setLimitParameters(
        period_limit, period_duration, {"from": set_limits_role_holder}
    )

    spending = 1 * 10**18
    spendable = period_limit - spending
    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.spendableBalance() == spendable
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == spendable

    new_period_limit = 2 * spending
    new_spendable = new_period_limit - spending
    # NB!: already spent amount decreased to the new limit
    new_spending = spending
    limits_checker.setLimitParameters(
        new_period_limit, period_duration, {"from": set_limits_role_holder}
    )
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == new_spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == new_spendable
    assert limits_checker.spendableBalance() == new_spendable


@pytest.mark.parametrize(
    "initial_period_duration,new_period_duration",
    [(3, 2), (3, 6), (12, 1), (1, 12)],
)
def test_spendable_amount_renewal_if_period_duration_changed(
    limits_checker, initial_period_duration, new_period_duration
):
    (limits_checker, set_limits_role_holder, update_spent_amount_role_holder) = limits_checker
    period_limit = 3 * 10**18

    limits_checker.setLimitParameters(
        period_limit, initial_period_duration, {"from": set_limits_role_holder}
    )

    spending = period_limit
    spendable = period_limit - spending
    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})
    assert limits_checker.spendableBalance() == spendable
    assert limits_checker.getPeriodState()["_alreadySpentAmount"] == spending
    assert limits_checker.getPeriodState()["_spendableBalanceInPeriod"] == spendable

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(1, {"from": update_spent_amount_role_holder})

    limits_checker.setLimitParameters(
        period_limit, new_period_duration, {"from": set_limits_role_holder}
    )
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(1, {"from": update_spent_amount_role_holder})

    advance_chain_time_to_beginning_of_the_next_period(new_period_duration)

    limits_checker.updateSpentAmount(spending, {"from": update_spent_amount_role_holder})

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        limits_checker.updateSpentAmount(1, {"from": update_spent_amount_role_holder})


def test_fail_if_update_spent_amount_when_no_period_duration_set(limits_checker):
    (limits_checker, _, update_spent_amount_role_holder) = limits_checker

    with reverts("INVALID_PERIOD_DURATION"):
        limits_checker.updateSpentAmount(123, {"from": update_spent_amount_role_holder})


@pytest.mark.parametrize(
    "inputs, period_duration, expected_result",
    [
        [[1640995200, 1640998800, 1642208400, 1643670000, 1643673599], 1, 1640995200],
        [[1646092800, 1646096400, 1648774800, 1651359600, 1651363199], 2, 1646092800],
        [[1648771200, 1648774800, 1652576400, 1656630000, 1656633599], 3, 1648771200],
        [[1656633600, 1656637200, 1664586000, 1672527600, 1672531199], 6, 1656633600],
        [[1640995200, 1640998800, 1652576400, 1672527600, 1672531199], 12, 1640995200],
    ],
)
def test_period_start_from_timestamp(
    limits_checker_with_private_method_exposed, inputs, period_duration, expected_result
):
    (limits_checker, set_limits_role_holder, _) = limits_checker_with_private_method_exposed
    period_limit = 3 * 10**18

    for timestamp in inputs:
        limits_checker.setLimitParameters(
            period_limit, period_duration, {"from": set_limits_role_holder}
        )
        assert limits_checker.getPeriodStartFromTimestamp(timestamp) == expected_result

    assert (
        limits_checker.getPeriodStartFromTimestamp(inputs[0] - 3600) != expected_result
    )  # 1 hour before the period
    assert (
        limits_checker.getPeriodStartFromTimestamp(inputs[0] - 1) != expected_result
    )  # second before the period
    assert (
        limits_checker.getPeriodStartFromTimestamp(inputs[len(inputs) - 1] + 1) != expected_result
    )  # second after the period
    assert (
        limits_checker.getPeriodStartFromTimestamp(inputs[len(inputs) - 1] + 3600)
        != expected_result
    )  # hour after the period


@pytest.mark.parametrize(
    "inputs, period_duration, expected_result",
    [
        [[1640995200, 1640998800, 1642208400, 1643670000, 1643673599], 1, 1643673600],
        [[1646092800, 1646096400, 1648774800, 1651359600, 1651363199], 2, 1651363200],
        [[1648771200, 1648774800, 1652576400, 1656630000, 1656633599], 3, 1656633600],
        [[1656633600, 1656637200, 1664586000, 1672527600, 1672531199], 6, 1672531200],
        [[1640995200, 1640998800, 1652576400, 1672527600, 1672531199], 12, 1672531200],
    ],
)
def test_period_end_from_timestamp(
    limits_checker_with_private_method_exposed, inputs, period_duration, expected_result
):
    (limits_checker, set_limits_role_holder, _) = limits_checker_with_private_method_exposed
    period_limit = 3 * 10**18

    for timestamp in inputs:
        limits_checker.setLimitParameters(
            period_limit, period_duration, {"from": set_limits_role_holder}
        )
        assert limits_checker.getPeriodEndFromTimestamp(timestamp) == expected_result

    assert (
        limits_checker.getPeriodEndFromTimestamp(inputs[0] - 3600) != expected_result
    )  # hour before the period
    assert (
        limits_checker.getPeriodEndFromTimestamp(inputs[0] - 1) != expected_result
    )  # second before the period
    assert (
        limits_checker.getPeriodEndFromTimestamp(inputs[len(inputs) - 1] + 2) != expected_result
    )  # second after the period
    assert (
        limits_checker.getPeriodEndFromTimestamp(inputs[len(inputs) - 1] + 3600) != expected_result
    )  # hour after the period
