import pytest

from datetime import datetime, timezone, tzinfo
from dateutil.relativedelta import relativedelta
from brownie import interface
from brownie.test import given, strategy
from hypothesis import Verbosity, settings
from utils.test_helpers import get_timestamp_from_date


@pytest.mark.parametrize(
    "date",
    [(1970, 1, 1), (2024, 2, 29), (2023, 1, 1), (2023, 1, 1), (2022, 12, 31)],
)
def test_timestamp_to_date(date_time_library, date):
    assert date_time_library.timestampToDate(get_timestamp_from_date(*date)) == date


@pytest.mark.parametrize(
    "start_date,end_date",
    [[(2020, 1, 1), (2025, 1, 1)]],
)
def test_timestamp_to_date_automated(date_time_library, start_date, end_date):
    current_date = datetime(*start_date, tzinfo=timezone.utc)

    while datetime.timestamp(current_date) < get_timestamp_from_date(*end_date):
        assert date_time_library.timestampToDate(datetime.timestamp(current_date)) == (
            current_date.year,
            current_date.month,
            current_date.day,
        )

        current_date += relativedelta(days=+1)


@given(
    timestamp=strategy(
        "int",
        min_value=get_timestamp_from_date(2022, 1, 1),
        max_value=get_timestamp_from_date(2030, 1, 1),
    )
)
@settings(max_examples=5000, verbosity=Verbosity.quiet)
def test_property_based_timestamp_to_date(date_time_library, timestamp):
    current_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    assert date_time_library.timestampToDate(timestamp) == (
        current_date.year,
        current_date.month,
        current_date.day,
    )


@pytest.mark.parametrize(
    "date",
    [
        (1970, 1, 1),
        (2024, 2, 29),
        (2023, 1, 1),
        (2022, 12, 31),
    ],
)
# This method always returns timestamp of start of the day
def test_timestamp_from_date(date_time_library, date):
    assert date_time_library.timestampFromDate(*date) == get_timestamp_from_date(*date)


@pytest.mark.parametrize(
    "start_date,end_date",
    [[(2020, 1, 1), (2025, 1, 1)]],
)
def test_timestamp_from_date_automated(date_time_library, start_date, end_date):
    current_date = datetime(*start_date, tzinfo=timezone.utc)

    while datetime.timestamp(current_date) < get_timestamp_from_date(*end_date):
        assert date_time_library.timestampFromDate(
            current_date.year,
            current_date.month,
            current_date.day,
        ) == datetime.timestamp(current_date)

        current_date += relativedelta(days=+1)


TEST_START_DATE = datetime(2022, 1, 1, tzinfo=timezone.utc)
TEST_END_DATE = datetime(2030, 1, 1, tzinfo=timezone.utc)


@given(
    days_shift=strategy("int", min_value=0, max_value=(TEST_END_DATE - TEST_START_DATE).days),
)
@settings(max_examples=5000, verbosity=Verbosity.quiet)
def test_property_based_timestamp_from_date(date_time_library, days_shift):
    date = TEST_START_DATE + relativedelta(days=+days_shift)
    assert (
        date_time_library.timestampFromDate(date.year, date.month, date.day)
        == date.timestamp()
    )


@pytest.mark.parametrize(
    "start_date, months_to_add",
    [((2020, 1, 1), months) for months in [1, 2, 3, 6, 8, 12, 24]]  # First day of month
    + [((2020, 1, 31), months) for months in [1, 2, 3, 6, 8, 12, 24]],  # Last day of month
)
def test_add_month(date_time_library, start_date, months_to_add):
    current_point = datetime(*start_date, tzinfo=timezone.utc)

    num_subsequent_add_months_calls = 120
    for _ in range(num_subsequent_add_months_calls):
        assert datetime.timestamp(
            current_point + relativedelta(months=+months_to_add)
        ) == date_time_library.addMonths(datetime.timestamp(current_point), months_to_add)

        current_point += relativedelta(months=+1)


@pytest.fixture(scope="module")
def date_time_library(bokkyPooBahsDateTimeContract):
    return interface.IBokkyPooBahsDateTimeContract(bokkyPooBahsDateTimeContract)
