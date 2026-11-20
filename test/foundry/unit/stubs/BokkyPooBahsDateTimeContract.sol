// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {
    IBokkyPooBahsDateTimeContract
} from "contracts/interfaces/IBokkyPooBahsDateTimeContract.sol";

/// @notice Stands in for the deployed BokkyPooBahsDateTimeContract `LimitsChecker` takes calendar
/// dates from.
/// @dev The three `IBokkyPooBahsDateTimeContract` methods, with the day-number arithmetic of
/// BokkyPooBah's DateTime Library v1.01 kept as published.
contract BokkyPooBahsDateTimeContract is IBokkyPooBahsDateTimeContract {
    uint256 private constant SECONDS_PER_DAY = 24 * 60 * 60;
    int256 private constant OFFSET19700101 = 2440588;

    function timestampToDate(uint256 timestamp)
        external
        pure
        override
        returns (uint256 year, uint256 month, uint256 day)
    {
        (year, month, day) = _daysToDate(timestamp / SECONDS_PER_DAY);
    }

    function timestampFromDate(uint256 year, uint256 month, uint256 day)
        external
        pure
        override
        returns (uint256 timestamp)
    {
        timestamp = _daysFromDate(year, month, day) * SECONDS_PER_DAY;
    }

    function addMonths(uint256 timestamp, uint256 _months)
        external
        pure
        override
        returns (uint256 newTimestamp)
    {
        (uint256 year, uint256 month, uint256 day) = _daysToDate(timestamp / SECONDS_PER_DAY);
        month += _months;
        year += (month - 1) / 12;
        month = ((month - 1) % 12) + 1;
        uint256 daysInMonth = _getDaysInMonth(year, month);
        if (day > daysInMonth) {
            day = daysInMonth;
        }
        newTimestamp =
            _daysFromDate(year, month, day) * SECONDS_PER_DAY + (timestamp % SECONDS_PER_DAY);
        require(newTimestamp >= timestamp);
    }

    // Days from 1970/01/01 to year/month/day by the date conversion algorithm from
    // http://aa.usno.navy.mil/faq/docs/JD_Formula.php, minus the offset 2440588 so that
    // 1970/01/01 is day 0
    function _daysFromDate(uint256 year, uint256 month, uint256 day)
        private
        pure
        returns (uint256 _days)
    {
        require(year >= 1970);
        int256 _year = int256(year);
        int256 _month = int256(month);
        int256 _day = int256(day);

        int256 __days = _day - 32075 + (1461 * (_year + 4800 + (_month - 14) / 12)) / 4
            + (367 * (_month - 2 - ((_month - 14) / 12) * 12)) / 12
            - (3 * ((_year + 4900 + (_month - 14) / 12) / 100)) / 4 - OFFSET19700101;

        _days = uint256(__days);
    }

    // Year/month/day from the days since 1970/01/01 by the date conversion algorithm from
    // http://aa.usno.navy.mil/faq/docs/JD_Formula.php, plus the offset 2440588 so that
    // 1970/01/01 is day 0
    function _daysToDate(uint256 _days)
        private
        pure
        returns (uint256 year, uint256 month, uint256 day)
    {
        int256 __days = int256(_days);

        int256 L = __days + 68569 + OFFSET19700101;
        int256 N = (4 * L) / 146097;
        L = L - (146097 * N + 3) / 4;
        int256 _year = (4000 * (L + 1)) / 1461001;
        L = L - (1461 * _year) / 4 + 31;
        int256 _month = (80 * L) / 2447;
        int256 _day = L - (2447 * _month) / 80;
        L = _month / 11;
        _month = _month + 2 - 12 * L;
        _year = 100 * (N - 49) + _year + L;

        year = uint256(_year);
        month = uint256(_month);
        day = uint256(_day);
    }

    function _isLeapYear(uint256 year) private pure returns (bool leapYear) {
        leapYear = ((year % 4 == 0) && (year % 100 != 0)) || (year % 400 == 0);
    }

    function _getDaysInMonth(uint256 year, uint256 month)
        private
        pure
        returns (uint256 daysInMonth)
    {
        if (
            month == 1 || month == 3 || month == 5 || month == 7 || month == 8 || month == 10
                || month == 12
        ) {
            daysInMonth = 31;
        } else if (month != 2) {
            daysInMonth = 30;
        } else {
            daysInMonth = _isLeapYear(year) ? 29 : 28;
        }
    }
}
