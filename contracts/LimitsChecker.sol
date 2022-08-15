// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./libraries/EVMScriptCreator.sol";
import "./libraries/BokkyPooBahsDateTimeLibrary.sol";
import "./EasyTrack.sol";

/// @author zuzueeka
/// @notice Stores limits params and checks limits
abstract contract LimitsChecker {
    // -------------
    // EVENTS
    // -------------

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_WRONG_PERIOD_DURATION = "WRONG_PERIOD_DURATION";
    string private constant ERROR_MOTION_IS_OVERDUE = "MOTION_IS_OVERDUE";

    // -------------
    // ROLES
    // -------------

    // -------------
    // CONSTANTS
    // -------------

    // ------------
    // STORAGE VARIABLES
    // ------------

    /// @notice Address of EasyTrack
    EasyTrack public immutable easyTrack;

    /// @notice Length of period in months
    uint256 internal periodDurationMonth;

    /// @notice The maximum that can be spent in a period
    uint256 internal limit;

    /// @notice Amount already spent in the period. Key - start date of the period, value - amount.
    mapping(uint256 => uint256) public spentInPeriod;

    // ------------
    // CONSTRUCTOR
    // ------------
    constructor(EasyTrack _easy_track) {
        easyTrack = _easy_track;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Checks if _paymentSum is less than may be spent in the period that contains _startDate
    /// @param _paymentSum Motion sum
    /// @param _startDate Motion start date
    /// @return True if _paymentSum is less than may be spent in the period that contains _startDate
    function isUnderLimitInPeriod(uint256 _paymentSum, uint256 _startDate)
        external
        view
        returns (bool)
    {
        return _paymentSum <= limit - spentInPeriod[_budgetPeriod(_startDate)];
    }

    /// @notice Increases amount spent in the period that contains _startDate on _paymentSum
    /// @param _paymentSum Motion sum
    /// @param _startDate Motion start date
    function updateSpentInPeriod(uint256 _paymentSum, uint256 _startDate) external {
        uint256 _motionDuration = easyTrack.motionDuration();
        require(
            _startDate >= block.timestamp - 2 * _motionDuration * 60 * 60,
            ERROR_MOTION_IS_OVERDUE
        );
        spentInPeriod[_budgetPeriod(_startDate)] += _paymentSum;
    }

    /// @notice Sets limit as _limit
    /// @param _limit Limit to set
    function setLimit(uint256 _limit) external {
        limit = _limit;
    }

    /// @notice Returns current limit
    /// @return The maximum that can be spent in a period
    function getLimit() external view returns (uint256) {
        return limit;
    }

    /// @notice Returns current balance in the _budgetPeriod
    /// @param _budgetPeriod Time stamp of the start date of the period
    /// @return Balance of the budget in a given period
    function currentBudgetBalance(uint256 _budgetPeriod) external view returns (uint256) {
        return limit - spentInPeriod[_budgetPeriod];
    }

    /// @notice Sets PeriodDurationMonth
    /// @param _period Period in months to set
    function setPeriodDurationMonth(uint256 _period) external {
        _checkPeriodDurationMonth(_period);
        periodDurationMonth = _period;
    }

    /// @notice Returns PeriodDurationMonth
    /// @return Length of period in months
    function getPeriodDurationMonth() external view returns (uint256) {
        return periodDurationMonth;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    // returns the beginning of the period in which the _timestamp is located
    function _budgetPeriod(uint256 _timestamp) internal view returns (uint256) {
        _checkPeriodDurationMonth(periodDurationMonth);

        (uint256 year, uint256 month, ) = BokkyPooBahsDateTimeLibrary.timestampToDate(_timestamp);

        return
            BokkyPooBahsDateTimeLibrary.timestampFromDate(
                year,
                month - ((month - 1) % periodDurationMonth),
                1
            );
    }

    function _checkPeriodDurationMonth(uint256 _periodDurationMonth) internal view {
        require(
            _periodDurationMonth == 1 ||
                _periodDurationMonth == 3 ||
                _periodDurationMonth == 6 ||
                _periodDurationMonth == 12,
            ERROR_WRONG_PERIOD_DURATION
        );
    }
}
