from utils import log
from datetime import datetime, timezone, timedelta

CANCEL_ROLE = "0x9f959e00d95122f5cbd677010436cf273ef535b86b056afc172852144b9491d7"
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"
UNPAUSE_ROLE = "0x265b220c5a8891efdd9e1b1b7fa72f257bd5169f8d87e319cf3dad6ff52b94ae"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"
SET_LIMIT_PARAMETERS_ROLE = "0x389c107d46e44659ea9e3d38a2e43f5414bdd0fd8244fa558561536ea90c2ece"
UPDATE_SPENDABLE_BALANCE_ROLE = "0x23cee4c317ad989ca27616d7d935a03cd12dad9d4b8e7fb9546389cb7fbbb9c9"
ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = "0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276"
REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE = "0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b"
PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"


def access_control_revert_message(sender, role=DEFAULT_ADMIN_ROLE):
    PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"
    return PERMISSION_ERROR_TEMPLATE % (sender.address.lower(), role)


def assert_equals(desc, actual, expected):
    assert actual == expected
    log.ok(desc, actual)


def assert_single_event(receipt, event_name, args: dict):
    assert len(receipt.events) == 1, f"event '{event_name}' must exist and be single"
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
