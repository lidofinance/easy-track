import pytest

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from brownie import interface
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
