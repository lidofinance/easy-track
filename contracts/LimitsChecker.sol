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
    string private constant ERROR_SUM_EXCEEDS_LIMIT = "SUM_EXCEEDS_LIMIT";

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

    /// @notice End of the current period
    uint256 internal periodEnd;

    /// @notice The maximum that can be spent in a period
    uint256 internal limit;

    /// @notice Amount already spent in the period. Key - start date of the period, value - amount.
    uint256 internal spent;

    // ------------
    // CONSTRUCTOR
    // ------------
    constructor(EasyTrack _easy_track) {
        easyTrack = _easy_track;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Checks if _paymentSum is less than may be spent in the period
    /// @param _paymentSum Motion sum
    /// @return True if _paymentSum is less than may be spent in the period
    function isUnderLimit(uint256 _paymentSum) external view returns (bool) {
        uint256 _motionDuration = easyTrack.motionDuration();
        if (block.timestamp + _motionDuration > periodEnd) {
            return _paymentSum <= limit;
        } else {
            return _paymentSum <= limit - spent;
        }
    }

    function checkAndUpdateLimits(uint256 _paymentSum) external {
        _checkAndUpdateLimitParameters();
        _checkLimit(_paymentSum);
        _writeOffBudget(_paymentSum);
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

    /// @notice Returns current balance
    /// @return Balance of the budget
    function currentBudgetBalance() external view returns (uint256) {
        return limit - spent;
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

    /// @notice Sets periodEnd
    /// @param _period timestamp to set as end of the period
    function setPeriodEnd(uint256 _period) public {
        periodEnd = _period;
    }

    /// @notice Returns periodEnd
    /// @return End of the current budget period
    function getPeriodEnd() public view returns (uint256) {
        return periodEnd;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _checkAndUpdateLimitParameters() internal {
        _checkPeriodDurationMonth(periodDurationMonth);
        while (block.timestamp > periodEnd) {
            periodEnd = BokkyPooBahsDateTimeLibrary.addMonths(periodEnd - 1, periodDurationMonth);
            spent = 0;
        }
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

    function _checkLimit(uint256 _paymentSum) internal view {
        require(_paymentSum <= limit - spent, ERROR_SUM_EXCEEDS_LIMIT);
    }

    function _writeOffBudget(uint256 _paymentSum) internal {
        spent += _paymentSum;
    }
}
