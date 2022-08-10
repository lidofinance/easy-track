// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./libraries/EVMScriptCreator.sol";
import "./EasyTrack.sol";

abstract contract LimitsChecker {
    EasyTrack public immutable EASY_TRACK;

    uint256 constant SECONDS_PER_DAY = 24 * 60 * 60;
    int256 constant OFFSET19700101 = 2440588;

    uint16 periodDurationMonth;
    uint256 limit;

    mapping(uint256 => uint256) public spentInPeriod;

    // -------------
    // EXTERNAL METHODS
    // -------------

    constructor(EasyTrack _easy_track) {
        EASY_TRACK = _easy_track;
    }

    /// @notice
    function isUnderLimitInPeriod(uint256 _paymentSum, uint256 _startDate)
        external
        view
        returns (bool)
    {
        return _paymentSum <= limit - spentInPeriod[_budgetPeriod(_startDate)];
    }

    function updateSpentInPeriod(
        uint256 _paymentSum,
        uint256 _startDate,
        uint256 _motionDuration
    ) external {
        require(_startDate >= block.timestamp - 2 * _motionDuration * 60 * 60, "MOTION_IS_OVERDUE");
        spentInPeriod[_budgetPeriod(_startDate)] += _paymentSum;
    }

    function setLimit(uint256 _limit) external {
        limit = _limit;
    }

    function currentBudgetBalance(uint256 budgetPeriod) external view returns (uint256) {
        return limit - spentInPeriod[budgetPeriod];
    }

    function setPeriodDurationMonth(uint16 _period) external {
        require(
            _period == 1 || _period == 3 || _period == 6 || _period == 12,
            "WRONG_periodDurationMonth"
        );
        periodDurationMonth = _period;
    }

    function getPeriodDurationMonth() external view returns (uint16) {
        return periodDurationMonth;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _budgetPeriod(uint256 _timestamp) internal view returns (uint256) {
        require(
            periodDurationMonth == 1 ||
                periodDurationMonth == 3 ||
                periodDurationMonth == 6 ||
                periodDurationMonth == 12,
            "WRONG_periodDurationMonth"
        );

        (uint256 year, uint256 month, ) = _daysToDate(_timestamp / SECONDS_PER_DAY);
        return
            _daysFromDate(year, month - ((month - 1) % periodDurationMonth), 1) * SECONDS_PER_DAY;
    }

    // ------------------------------------------------------------------------
    // Calculate the number of days from 1970/01/01 to year/month/day using
    // the date conversion algorithm from
    //   https://aa.usno.navy.mil/faq/JD_formula.html
    // and subtracting the offset 2440588 so that 1970/01/01 is day 0
    //
    // days = day
    //      - 32075
    //      + 1461 * (year + 4800 + (month - 14) / 12) / 4
    //      + 367 * (month - 2 - (month - 14) / 12 * 12) / 12
    //      - 3 * ((year + 4900 + (month - 14) / 12) / 100) / 4
    //      - offset
    // ------------------------------------------------------------------------
    function _daysFromDate(
        uint256 year,
        uint256 month,
        uint256 day
    ) internal pure returns (uint256 _days) {
        require(year >= 1970);
        int256 _year = int256(year);
        int256 _month = int256(month);
        int256 _day = int256(day);

        int256 __days = _day -
            32075 +
            (1461 * (_year + 4800 + (_month - 14) / 12)) /
            4 +
            (367 * (_month - 2 - ((_month - 14) / 12) * 12)) /
            12 -
            (3 * ((_year + 4900 + (_month - 14) / 12) / 100)) /
            4 -
            OFFSET19700101;

        _days = uint256(__days);
    }

    // ------------------------------------------------------------------------
    // Calculate year/month/day from the number of days since 1970/01/01 using
    // the date conversion algorithm from
    //   http://aa.usno.navy.mil/faq/docs/JD_Formula.php
    // and adding the offset 2440588 so that 1970/01/01 is day 0
    //
    // int L = days + 68569 + offset
    // int N = 4 * L / 146097
    // L = L - (146097 * N + 3) / 4
    // year = 4000 * (L + 1) / 1461001
    // L = L - 1461 * year / 4 + 31
    // month = 80 * L / 2447
    // dd = L - 2447 * month / 80
    // L = month / 11
    // month = month + 2 - 12 * L
    // year = 100 * (N - 49) + year + L
    // ------------------------------------------------------------------------
    function _daysToDate(uint256 _days)
        internal
        pure
        returns (
            uint256 year,
            uint256 month,
            uint256 day
        )
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
}
