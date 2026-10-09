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

contract BokkyPooBahsDateTimeContractTest is Test {
    uint256 internal constant TEST_START_DATE = 1640995200; // 2022-01-01 00:00:00 UTC
    uint256 internal constant TEST_END_DATE = 1893456000; // 2030-01-01 00:00:00 UTC
    uint256 internal constant NUM_SUBSEQUENT_ADD_MONTHS_CALLS = 120;

    IBokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;

    function setUp() public {
        bokkyPooBahsDateTimeContract = new BokkyPooBahsDateTimeContract();

        vm.label(address(bokkyPooBahsDateTimeContract), "BokkyPooBahsDateTimeContract");
    }

    // python: test_timestamp_to_date[date0]
    function test_TimestampToDate_1970_01_01() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(1970, 1, 1), 1970, 1, 1);
    }

    // python: test_timestamp_to_date[date1]
    function test_TimestampToDate_2024_02_29() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(2024, 2, 29), 2024, 2, 29);
    }

    // python: test_timestamp_to_date[date2], which date3 repeats verbatim
    function test_TimestampToDate_2023_01_01() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(2023, 1, 1), 2023, 1, 1);
    }

    // python: test_timestamp_to_date[date4]
    function test_TimestampToDate_2022_12_31() external view {
        _assertTimestampToDate(Calendar.timestampFromDate(2022, 12, 31), 2022, 12, 31);
    }

    // python: test_timestamp_to_date_automated[start_date0-end_date0]
    function test_TimestampToDateForEveryDayFrom2020To2025() external view {
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

    // python: test_property_based_timestamp_to_date
    /// forge-config: unit.fuzz.runs = 5000
    function testFuzz_TimestampToDate(uint256 timestamp) external view {
        timestamp = bound(timestamp, TEST_START_DATE, TEST_END_DATE);

        (uint256 year, uint256 month, uint256 day) = Calendar.dateFromTimestamp(timestamp);

        _assertTimestampToDate(timestamp, year, month, day);
    }

    // python: test_timestamp_from_date[date0]
    function test_TimestampFromDate_1970_01_01() external view {
        _assertTimestampFromDate(1970, 1, 1);
    }

    // python: test_timestamp_from_date[date1]
    function test_TimestampFromDate_2024_02_29() external view {
        _assertTimestampFromDate(2024, 2, 29);
    }

    // python: test_timestamp_from_date[date2]
    function test_TimestampFromDate_2023_01_01() external view {
        _assertTimestampFromDate(2023, 1, 1);
    }

    // python: test_timestamp_from_date[date3]
    function test_TimestampFromDate_2022_12_31() external view {
        _assertTimestampFromDate(2022, 12, 31);
    }

    // python: test_timestamp_from_date_automated[start_date0-end_date0]
    function test_TimestampFromDateForEveryDayFrom2020To2025() external view {
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

    // python: test_property_based_timestamp_from_date
    /// forge-config: unit.fuzz.runs = 5000
    function testFuzz_TimestampFromDate(uint256 daysShift) external view {
        daysShift = bound(daysShift, 0, (TEST_END_DATE - TEST_START_DATE) / 1 days);

        uint256 timestamp = TEST_START_DATE + daysShift * 1 days;
        (uint256 year, uint256 month, uint256 day) = Calendar.dateFromTimestamp(timestamp);

        assertEq(
            bokkyPooBahsDateTimeContract.timestampFromDate(year, month, day),
            timestamp,
            "timestampFromDate"
        );
    }

    // python: test_add_month, start_date (2020, 1, 1), months_to_add 1
    function test_AddMonthsFromFirstDayOfMonth_1() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 1);
    }

    // python: test_add_month, start_date (2020, 1, 1), months_to_add 2
    function test_AddMonthsFromFirstDayOfMonth_2() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 2);
    }

    // python: test_add_month, start_date (2020, 1, 1), months_to_add 3
    function test_AddMonthsFromFirstDayOfMonth_3() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 3);
    }

    // python: test_add_month, start_date (2020, 1, 1), months_to_add 6
    function test_AddMonthsFromFirstDayOfMonth_6() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 6);
    }

    // python: test_add_month, start_date (2020, 1, 1), months_to_add 8
    function test_AddMonthsFromFirstDayOfMonth_8() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 8);
    }

    // python: test_add_month, start_date (2020, 1, 1), months_to_add 12
    function test_AddMonthsFromFirstDayOfMonth_12() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 12);
    }

    // python: test_add_month, start_date (2020, 1, 1), months_to_add 24
    function test_AddMonthsFromFirstDayOfMonth_24() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 1), 24);
    }

    // python: test_add_month, start_date (2020, 1, 31), months_to_add 1
    function test_AddMonthsFromLastDayOfMonth_1() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 1);
    }

    // python: test_add_month, start_date (2020, 1, 31), months_to_add 2
    function test_AddMonthsFromLastDayOfMonth_2() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 2);
    }

    // python: test_add_month, start_date (2020, 1, 31), months_to_add 3
    function test_AddMonthsFromLastDayOfMonth_3() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 3);
    }

    // python: test_add_month, start_date (2020, 1, 31), months_to_add 6
    function test_AddMonthsFromLastDayOfMonth_6() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 6);
    }

    // python: test_add_month, start_date (2020, 1, 31), months_to_add 8
    function test_AddMonthsFromLastDayOfMonth_8() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 8);
    }

    // python: test_add_month, start_date (2020, 1, 31), months_to_add 12
    function test_AddMonthsFromLastDayOfMonth_12() external view {
        _assertAddMonthsAlongMonthlyWalk(Calendar.timestampFromDate(2020, 1, 31), 12);
    }

    // python: test_add_month, start_date (2020, 1, 31), months_to_add 24
    function test_AddMonthsFromLastDayOfMonth_24() external view {
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
