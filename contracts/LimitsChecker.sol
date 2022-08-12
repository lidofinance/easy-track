// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./libraries/EVMScriptCreator.sol";
import "./libraries/BokkyPooBahsDateTimeLibrary.sol";
import "./EasyTrack.sol";

abstract contract LimitsChecker {
    EasyTrack public immutable EASY_TRACK;

    uint256 constant SECONDS_PER_DAY = 24 * 60 * 60;

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

        (uint256 year, uint256 month, ) = BokkyPooBahsDateTimeLibrary._daysToDate(
            _timestamp / SECONDS_PER_DAY
        );

        return
            BokkyPooBahsDateTimeLibrary._daysFromDate(
                year,
                month - ((month - 1) % periodDurationMonth),
                1
            ) * SECONDS_PER_DAY;
    }
}
