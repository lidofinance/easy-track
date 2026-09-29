// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Vm} from "forge-std/Vm.sol";
import {Calendar} from "test/foundry/unit/helpers/Calendar.sol";

/// @notice Ports of `utils/test_helpers.py`
library TestHelpers {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    /// @dev python: get_date_in_next_period caps the day of the month here
    uint256 private constant MAX_DAY_IN_NEXT_PERIOD = 28;

    /// @dev python: access_revert_message. The OpenZeppelin v4 AccessControl reason. The account
    /// is lowercased because `vm.toString` checksums it and `Strings.toHexString` does not
    function accessRevertMessage(address sender, bytes32 role)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(
            "AccessControl: account ",
            vm.toLowercase(vm.toString(sender)),
            " is missing role ",
            vm.toString(role)
        );
    }

    /// @dev python: get_month_start_timestamp. The first second of the month `timestamp` falls in
    function getMonthStartTimestamp(uint256 timestamp) internal pure returns (uint256) {
        (uint256 year, uint256 month,) = Calendar.dateFromTimestamp(timestamp);
        return Calendar.timestampFromDate(year, month, 1);
    }

    /// @dev python: get_date_in_next_period. The same time of day `periodDurationMonths` months
    /// after `timestamp`, on the same day of the month capped at the 28th
    function getDateInNextPeriod(uint256 timestamp, uint256 periodDurationMonths)
        internal
        pure
        returns (uint256)
    {
        (uint256 year, uint256 month, uint256 day) = Calendar.dateFromTimestamp(timestamp);
        uint256 nextMonthUnlimitedFromZero = month + (periodDurationMonths - 1);
        uint256 nextMonth = 1 + (nextMonthUnlimitedFromZero % Calendar.MONTHS_PER_YEAR);
        uint256 nextYear = nextMonthUnlimitedFromZero >= Calendar.MONTHS_PER_YEAR ? year + 1 : year;
        uint256 nextDay = day < MAX_DAY_IN_NEXT_PERIOD ? day : MAX_DAY_IN_NEXT_PERIOD;

        return Calendar.timestampFromDate(nextYear, nextMonth, nextDay) + (timestamp % 1 days);
    }

    /// @dev python: calc_period_first_month. The hard-coded table, on purpose not the formula of
    /// `LimitsChecker._getFirstMonthInPeriodFromMonth` it mirrors
    function calcPeriodFirstMonth(uint256 periodDuration, uint256 currentMonth)
        internal
        pure
        returns (uint256)
    {
        uint8[12] memory firstMonths;
        if (periodDuration == 1) {
            firstMonths = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        } else if (periodDuration == 2) {
            firstMonths = [1, 1, 3, 3, 5, 5, 7, 7, 9, 9, 11, 11];
        } else if (periodDuration == 3) {
            firstMonths = [1, 1, 1, 4, 4, 4, 7, 7, 7, 10, 10, 10];
        } else if (periodDuration == 6) {
            firstMonths = [1, 1, 1, 1, 1, 1, 7, 7, 7, 7, 7, 7];
        } else if (periodDuration == 12) {
            firstMonths = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1];
        } else {
            revert("PERIOD_DURATION_NOT_IN_TABLE");
        }
        return firstMonths[currentMonth - 1];
    }

    /// @dev python: calc_period_range, in pure UTC where the Python reads the local calendar first
    function calcPeriodRange(uint256 periodDuration, uint256 nowTimestamp)
        internal
        pure
        returns (uint256 periodStart, uint256 periodEnd)
    {
        (uint256 year, uint256 month,) = Calendar.dateFromTimestamp(nowTimestamp);
        uint256 firstMonth = calcPeriodFirstMonth(periodDuration, month);
        periodStart = Calendar.timestampFromDate(year, firstMonth, 1);
        periodEnd = getMonthStartTimestamp(getDateInNextPeriod(periodStart, periodDuration));
    }

    /// @dev python: advance_chain_time_to_beginning_of_the_next_period. Warps to the first second
    /// of the period after the one `block.timestamp` falls in
    function advanceChainTimeToBeginningOfTheNextPeriod(uint256 periodDuration) internal {
        (, uint256 firstSecondOfNextPeriod) =
            calcPeriodRange(periodDuration, vm.getBlockTimestamp());
        vm.warp(firstSecondOfNextPeriod);
    }
}
