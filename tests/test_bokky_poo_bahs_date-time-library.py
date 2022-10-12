import pytest

from datetime import datetime
from dateutil.relativedelta import relativedelta
from brownie import interface


@pytest.mark.parametrize(
    "timestamp,expected_date",
    [
        (0, (1970, 1, 1)),
        (1709164800, (2024, 2, 29)),  # leap year
        (1672531200, (2023, 1, 1)),  # 1 Jan start of the day
        (1672617570, (2023, 1, 1)),  # 1 Jan end of the day
        (1672531170, (2022, 12, 31)),  # 31 Dec end of the day
    ],
)
def test_timestamp_to_date(date_time_library, timestamp, expected_date):
    assert date_time_library.timestampToDate(timestamp) == expected_date


@pytest.mark.parametrize(
    "start_date,end_date",
    [[1577836800, 1735689600]],
)
def test_timestamp_to_date_automated(date_time_library, start_date, end_date):
    current_date = datetime.fromtimestamp(start_date)

    while datetime.timestamp(current_date) < end_date:
        assert date_time_library.timestampToDate(datetime.timestamp(current_date)) == (
            current_date.year,
            current_date.month,
            current_date.day,
        )

        current_date += relativedelta(days=+1)


@pytest.mark.parametrize(
    "date, expected_timestamp",
    [
        ((1970, 1, 1), 0),
        ((2024, 2, 29), 1709164800),  # 29 Feb start of the day of leap year
        ((2023, 1, 1), 1672531200),  # 1 Jan start of the day
        ((2022, 12, 31), 1672444800),  # 31 Dec start of the day
    ],
)
# This method always returns timestamp of start of the day
def test_timestamp_from_date(date_time_library, date, expected_timestamp):
    assert date_time_library.timestampFromDate(*date) == expected_timestamp


@pytest.mark.parametrize(
    "start_date,end_date",
    [[1577836800, 1735689600]],
)
def test_timestamp_from_date_automated(date_time_library, start_date, end_date):
    current_date = datetime.fromtimestamp(start_date)

    while datetime.timestamp(current_date) < end_date:
        assert date_time_library.timestampFromDate(
            current_date.year,
            current_date.month,
            current_date.day,
        ) == datetime.timestamp(current_date)

        current_date += relativedelta(days=+1)


@pytest.mark.parametrize(
    "start_timestamp, months_to_add",
    [(1577836800, months) for months in [1, 2, 3, 6, 8, 12, 24]]  # First day of month
    + [(1580428800, months) for months in [1, 2, 3, 6, 8, 12, 24]],  # Last day of month
)
def test_add_month(date_time_library, start_timestamp, months_to_add):
    current_point = datetime.fromtimestamp(start_timestamp)

    num_subsequent_add_months_calls = 120
    for _ in range(num_subsequent_add_months_calls):
        assert datetime.timestamp(
            current_point + relativedelta(months=+months_to_add)
        ) == date_time_library.addMonths(datetime.timestamp(current_point), months_to_add)

        current_point += relativedelta(months=+1)


@pytest.fixture(scope="module")
def date_time_library(bokkyPooBahsDateTimeContract):
    return interface.IBokkyPooBahsDateTimeContract(bokkyPooBahsDateTimeContract)
