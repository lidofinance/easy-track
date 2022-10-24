from datetime import datetime, timezone, timedelta

from brownie import chain

from utils import log

CANCEL_ROLE = "0x9f959e00d95122f5cbd677010436cf273ef535b86b056afc172852144b9491d7"
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"
UNPAUSE_ROLE = "0x265b220c5a8891efdd9e1b1b7fa72f257bd5169f8d87e319cf3dad6ff52b94ae"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"
SET_LIMIT_PARAMETERS_ROLE = "0x389c107d46e44659ea9e3d38a2e43f5414bdd0fd8244fa558561536ea90c2ece"
UPDATE_SPENT_AMOUNT_ROLE = "0xc5260260446719a726d11a6faece21d19daa48b4cbcca118345832d4cb71df99"
ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = (
    "0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276"
)
REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE = (
    "0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b"
)
PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"


def access_revert_message(sender, role=DEFAULT_ADMIN_ROLE):
    """Format access error message crafted by OpenZeppelin/AccessControl contract"""
    PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"
    return PERMISSION_ERROR_TEMPLATE % (sender.address.lower(), role)


def assert_equals(desc, actual, expected):
    assert actual == expected
    log.ok(desc, actual)


def assert_single_event(receipt, event_name, args: dict):
    assert (
        len(receipt.events) == 1
    ), f"event '{event_name}' must exist and be single (all events: {', '.join(receipt.events.keys())})"
    assert dict(receipt.events[event_name]) == args, f"incorrect event '{event_name}' arguments"


def assert_event_exists(receipt, event_name, args: dict):
    assert dict(receipt.events[event_name]) == args, f"incorrect event '{event_name}' arguments"


def get_month_start_timestamp(any_point_in_this_month: datetime):
    return int(
        any_point_in_this_month.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        ).timestamp()
    )


def get_date_in_next_period(any_point_in_this_month: datetime, period_duration_months: int):
    NUM_MONTHS = 12
    next_month_unlimited_from_zero = any_point_in_this_month.month + (period_duration_months - 1)
    next_month = 1 + (next_month_unlimited_from_zero % NUM_MONTHS)
    next_year = any_point_in_this_month.year
    if next_month_unlimited_from_zero >= NUM_MONTHS:
        next_year += 1

    return any_point_in_this_month.replace(
        year=next_year,
        month=next_month,
    )


def get_next_month_start_timestamp(any_point_in_this_month: datetime, num_months: int):
    NUM_MONTHS = 12
    next_month_unlimited_from_zero = any_point_in_this_month.month + (num_months - 1)
    next_month = 1 + (next_month_unlimited_from_zero % NUM_MONTHS)
    next_year = any_point_in_this_month.year
    if next_month_unlimited_from_zero >= NUM_MONTHS:
        next_year += 1

    return int(
        any_point_in_this_month.replace(
            year=next_year,
            month=next_month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=timezone.utc,
        ).timestamp()
    )


def calc_period_first_month(period_duration, current_month):
    """Calculates the same value as LimitsChecker/_getFirstMonthInPeriodFromMonth"""
    data = {
        (1, 1): 1,
        (1, 2): 2,
        (1, 3): 3,
        (1, 4): 4,
        (1, 5): 5,
        (1, 6): 6,
        (1, 7): 7,
        (1, 8): 8,
        (1, 9): 9,
        (1, 10): 10,
        (1, 11): 11,
        (1, 12): 12,
        (2, 1): 1,
        (2, 2): 1,
        (2, 3): 3,
        (2, 4): 3,
        (2, 5): 5,
        (2, 6): 5,
        (2, 7): 7,
        (2, 8): 7,
        (2, 9): 9,
        (2, 10): 9,
        (2, 11): 11,
        (2, 12): 11,
        (3, 1): 1,
        (3, 2): 1,
        (3, 3): 1,
        (3, 4): 4,
        (3, 5): 4,
        (3, 6): 4,
        (3, 7): 7,
        (3, 8): 7,
        (3, 9): 7,
        (3, 10): 10,
        (3, 11): 10,
        (3, 12): 10,
        (6, 1): 1,
        (6, 2): 1,
        (6, 3): 1,
        (6, 4): 1,
        (6, 5): 1,
        (6, 6): 1,
        (6, 7): 7,
        (6, 8): 7,
        (6, 9): 7,
        (6, 10): 7,
        (6, 11): 7,
        (6, 12): 7,
        (12, 1): 1,
        (12, 2): 1,
        (12, 3): 1,
        (12, 4): 1,
        (12, 5): 1,
        (12, 6): 1,
        (12, 7): 1,
        (12, 8): 1,
        (12, 9): 1,
        (12, 10): 1,
        (12, 11): 1,
        (12, 12): 1,
    }
    return data[(period_duration, current_month)]


def calc_period_range(period_duration: int, now_timestamp: int):
    """Calculates the same range as LimitsChecker.sol"""
    now = datetime.fromtimestamp(now_timestamp)
    first_month = calc_period_first_month(period_duration, now.month)
    first_month_date = now.replace(month=first_month)
    next_period_date = get_date_in_next_period(first_month_date, period_duration)

    return (
        get_month_start_timestamp(first_month_date),
        get_month_start_timestamp(next_period_date),
    )


def advance_chain_time_to_n_seconds_before_current_period_end(
    period_duration: int, seconds_before: int
):
    chain_now = chain.time()
    _, first_second_of_next_period = calc_period_range(period_duration, chain_now)
    seconds_till_period_end = first_second_of_next_period - 1 - chain_now
    assert (
        seconds_till_period_end > seconds_before
    ), f"cannot move chain time {seconds_before} seconds before current period \
         end, because there {seconds_till_period_end} seconds left till current period end"

    chain.sleep(seconds_till_period_end - seconds_before)
    assert chain.time() + seconds_before + 1 >= first_second_of_next_period


def advance_chain_time_to_beginning_of_the_next_period(period_duration: int):
    """Helps to avoid the situation when the tests run at the end of current period
    and the period advanced unexpectedly while the test was run and/or chain time
    advanced till the motion is ended.
    Advances to the first or the second day of the month roughly, just to avoid
    dealing with timezones"""

    chain_now = chain.time()
    _, first_second_of_next_period = calc_period_range(period_duration, chain_now)
    chain.sleep(first_second_of_next_period - chain_now)
    assert chain.time() >= first_second_of_next_period


# NOTE: helper uses UTC time format which fits to the blockchain timezone
def get_timestamp_from_date(year, month, day, hour=0, min=0, sec=0):
    return datetime(year, month, day, hour, min, sec, tzinfo=timezone.utc).timestamp()
