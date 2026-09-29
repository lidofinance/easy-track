// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Reference UTC calendar, the stand-in for Python's `datetime` and
/// `dateutil.relativedelta` in the date assertions.
/// @dev Counts days year by year and month by month, so it shares no arithmetic with the
/// day-number formulas of `BokkyPooBahsDateTimeContract` it is the oracle for.
library Calendar {
    uint256 internal constant EPOCH_YEAR = 1970;
    uint256 internal constant MONTHS_PER_YEAR = 12;

    /// @dev python: datetime(year, month, day, tzinfo=timezone.utc).timestamp()
    function timestampFromDate(uint256 year, uint256 month, uint256 day)
        internal
        pure
        returns (uint256)
    {
        return timestampFromDate(year, month, day, 0, 0, 0);
    }

    /// @dev python: datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp()
    function timestampFromDate(
        uint256 year,
        uint256 month,
        uint256 day,
        uint256 hour,
        uint256 minute,
        uint256 second
    ) internal pure returns (uint256) {
        uint256 daysSinceEpoch = day - 1;

        for (uint256 y = EPOCH_YEAR; y < year; ++y) {
            daysSinceEpoch += daysInYear(y);
        }

        for (uint256 m = 1; m < month; ++m) {
            daysSinceEpoch += daysInMonth(year, m);
        }

        return daysSinceEpoch * 1 days + hour * 1 hours + minute * 1 minutes + second;
    }

    /// @dev python: datetime.fromtimestamp(timestamp, tz=timezone.utc), as its year, month and day
    function dateFromTimestamp(uint256 timestamp)
        internal
        pure
        returns (uint256 year, uint256 month, uint256 day)
    {
        uint256 daysLeft = timestamp / 1 days;

        year = EPOCH_YEAR;
        while (daysLeft >= daysInYear(year)) {
            daysLeft -= daysInYear(year);
            ++year;
        }

        month = 1;
        while (daysLeft >= daysInMonth(year, month)) {
            daysLeft -= daysInMonth(year, month);
            ++month;
        }

        day = daysLeft + 1;
    }

    /// @dev python: datetime + relativedelta(months=+months). The day of the month is clamped to
    /// the length of the target month and the time of day is kept
    function addMonths(uint256 timestamp, uint256 months) internal pure returns (uint256) {
        (uint256 year, uint256 month, uint256 day) = dateFromTimestamp(timestamp);
        uint256 monthsFromZero = month - 1 + months;
        year += monthsFromZero / MONTHS_PER_YEAR;
        month = (monthsFromZero % MONTHS_PER_YEAR) + 1;

        uint256 daysInTargetMonth = daysInMonth(year, month);
        if (day > daysInTargetMonth) {
            day = daysInTargetMonth;
        }

        return timestampFromDate(year, month, day) + (timestamp % 1 days);
    }

    function daysInYear(uint256 year) internal pure returns (uint256) {
        return isLeapYear(year) ? 366 : 365;
    }

    function daysInMonth(uint256 year, uint256 month) internal pure returns (uint256) {
        if (month == 2) {
            return isLeapYear(year) ? 29 : 28;
        }
        if (month == 4 || month == 6 || month == 9 || month == 11) {
            return 30;
        }
        return 31;
    }

    function isLeapYear(uint256 year) internal pure returns (bool) {
        return (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
    }
}
