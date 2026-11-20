// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    IBokkyPooBahsDateTimeContract
} from "contracts/interfaces/IBokkyPooBahsDateTimeContract.sol";
import {
    BokkyPooBahsDateTimeContract
} from "test/foundry/unit/stubs/BokkyPooBahsDateTimeContract.sol";
import {Calendar} from "test/foundry/unit/helpers/Calendar.sol";

/// @notice `tests/test_bokky_poo_bahs_date-time-library.py` over the stub of `unit/stubs/` where
///         the Python runs against the mainnet deployment: a check of the stub the payouts unit
///         suites deploy against the day arithmetic of `helpers/Calendar.sol`.
contract BokkyPooBahsDateTimeContractTest is Test {
    uint256 internal constant TEST_START_DATE = 1640995200; // 2022-01-01 00:00:00 UTC
    uint256 internal constant TEST_END_DATE = 1893456000; // 2030-01-01 00:00:00 UTC
    uint256 internal constant NUM_SUBSEQUENT_ADD_MONTHS_CALLS = 120;

    IBokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;

    function setUp() public {
        bokkyPooBahsDateTimeContract = new BokkyPooBahsDateTimeContract();

        vm.label(address(bokkyPooBahsDateTimeContract), "BokkyPooBahsDateTimeContract");
    }

    function test_ConvertsTimestampToDate_1970_01_01() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(1970, 1, 1), 1970, 1, 1);
    }

    function test_ConvertsTimestampToDate_2024_02_29() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(2024, 2, 29), 2024, 2, 29);
    }

    function test_ConvertsTimestampToDate_2023_01_01() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(2023, 1, 1), 2023, 1, 1);
    }

    function test_ConvertsTimestampToDate_2022_12_31() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(2022, 12, 31), 2022, 12, 31);
    }

    function test_ConvertsTimestampToDateForEveryDayFrom2020To2025() external view {
        uint256 endTimestamp = Calendar.timestampFromDate(2025, 1, 1);

        for (
            uint256 timestamp = Calendar.timestampFromDate(2020, 1, 1);
            timestamp < endTimestamp;
            timestamp += 1 days
        ) {
            (uint256 year, uint256 month, uint256 day) = Calendar.dateFromTimestamp(timestamp);

            _assertTimestampToDate(timestamp, year, month, day);
        }
    }

    /// forge-config: default.fuzz.runs = 5000
    function testFuzz_ConvertsTimestampToDate(uint256 timestamp) external view {
        timestamp = bound(timestamp, TEST_START_DATE, TEST_END_DATE);

        (uint256 year, uint256 month, uint256 day) = Calendar.dateFromTimestamp(timestamp);

        _assertTimestampToDate(timestamp, year, month, day);
    }

    function test_ConvertsDateToTimestamp_1970_01_01() external view {
        _assertTimestampFromDate(1970, 1, 1);
    }

    function test_ConvertsDateToTimestamp_2024_02_29() external view {
        _assertTimestampFromDate(2024, 2, 29);
    }

    function test_ConvertsDateToTimestamp_2023_01_01() external view {
        _assertTimestampFromDate(2023, 1, 1);
    }

    function test_ConvertsDateToTimestamp_2022_12_31() external view {
        _assertTimestampFromDate(2022, 12, 31);
    }

    function test_ConvertsDateToTimestampForEveryDayFrom2020To2025() external view {
        uint256 endTimestamp = Calendar.timestampFromDate(2025, 1, 1);

        for (
            uint256 timestamp = Calendar.timestampFromDate(2020, 1, 1);
            timestamp < endTimestamp;
            timestamp += 1 days
        ) {
            (uint256 year, uint256 month, uint256 day) = Calendar.dateFromTimestamp(timestamp);

            assertEq(
                bokkyPooBahsDateTimeContract.timestampFromDate(year, month, day),
                timestamp,
                "timestampFromDate"
            );
        }
    }

    /// forge-config: default.fuzz.runs = 5000
    function testFuzz_ConvertsDateToTimestamp(uint256 daysShift) external view {
        daysShift = bound(daysShift, 0, (TEST_END_DATE - TEST_START_DATE) / 1 days);

        uint256 timestamp = TEST_START_DATE + daysShift * 1 days;
        (uint256 year, uint256 month, uint256 day) = Calendar.dateFromTimestamp(timestamp);

        assertEq(
            bokkyPooBahsDateTimeContract.timestampFromDate(year, month, day),
            timestamp,
            "timestampFromDate"
        );
    }

    function test_AddsMonthsFromFirstDayOfMonth_1() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 1);
    }

    function test_AddsMonthsFromFirstDayOfMonth_2() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 2);
    }

    function test_AddsMonthsFromFirstDayOfMonth_3() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 3);
    }

    function test_AddsMonthsFromFirstDayOfMonth_6() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 6);
    }

    function test_AddsMonthsFromFirstDayOfMonth_8() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 8);
    }

    function test_AddsMonthsFromFirstDayOfMonth_12() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 12);
    }

    function test_AddsMonthsFromFirstDayOfMonth_24() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 24);
    }

    function test_AddsMonthsFromLastDayOfMonth_1() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 1);
    }

    function test_AddsMonthsFromLastDayOfMonth_2() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 2);
    }

    function test_AddsMonthsFromLastDayOfMonth_3() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 3);
    }

    function test_AddsMonthsFromLastDayOfMonth_6() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 6);
    }

    function test_AddsMonthsFromLastDayOfMonth_8() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 8);
    }

    function test_AddsMonthsFromLastDayOfMonth_12() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 12);
    }

    function test_AddsMonthsFromLastDayOfMonth_24() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 24);
    }

    function _assertTimestampToDate(
        uint256 timestamp,
        uint256 expectedYear,
        uint256 expectedMonth,
        uint256 expectedDay
    ) private view {
        (uint256 year, uint256 month, uint256 day) =
            bokkyPooBahsDateTimeContract.timestampToDate(timestamp);

        assertEq(year, expectedYear, "year");
        assertEq(month, expectedMonth, "month");
        assertEq(day, expectedDay, "day");
    }

    function _assertTimestampFromDate(uint256 year, uint256 month, uint256 day) private view {
        assertEq(
            bokkyPooBahsDateTimeContract.timestampFromDate(year, month, day),
            Calendar.timestampFromDate(year, month, day),
            "timestampFromDate"
        );
    }

    /// @dev `addMonths` agrees with the reference calendar from each of 120 monthly points after
    /// `startTimestamp`. The walk itself steps by one month with the reference calendar, so from
    /// the 31st it clamps to the 29th of February and stays on the 29th from there
    function _assertAddMonthsAlongMonthlyWalk(uint256 startTimestamp, uint256 monthsToAdd)
        private
        view
    {
        uint256 currentPoint = startTimestamp;

        for (uint256 i; i < NUM_SUBSEQUENT_ADD_MONTHS_CALLS; ++i) {
            assertEq(
                bokkyPooBahsDateTimeContract.addMonths(currentPoint, monthsToAdd),
                Calendar.addMonths(currentPoint, monthsToAdd),
                "addMonths"
            );

            currentPoint = Calendar.addMonths(currentPoint, 1);
        }
    }
}
