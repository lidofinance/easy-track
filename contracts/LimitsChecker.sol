// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./libraries/EVMScriptCreator.sol";
import "./libraries/BokkyPooBahsDateTimeLibrary.sol";
import "./EasyTrack.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

/// @author zuzueeka
/// @notice Stores limits params and checks limits
abstract contract LimitsChecker is AccessControl {
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
    bytes32 public constant SET_LIMIT_PARAMETERS_ROLE = keccak256("SET_LIMIT_PARAMETERS_ROLE");
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
    uint256 internal currentPeriodEnd;

    /// @notice The maximum that can be spent in a period
    uint256 internal limit;

    /// @notice Amount already spent in the period. Key - start date of the period, value - amount.
    uint256 internal spent;

    // ------------
    // CONSTRUCTOR
    // ------------
    constructor(EasyTrack _easy_track, address[] memory _setLimitParametersRoleHolders) {
        easyTrack = _easy_track;
        for (uint256 i = 0; i < _setLimitParametersRoleHolders.length; i++) {
            _setupRole(SET_LIMIT_PARAMETERS_ROLE, _setLimitParametersRoleHolders[i]);
        }
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Checks if _payoutSum is less than may be spent in the period
    /// @param _payoutSum Motion sum
    /// @return True if _payoutSum is less than may be spent in the period
    function isUnderLimit(uint256 _payoutSum) external view returns (bool) {
        uint256 _motionDuration = easyTrack.motionDuration();
        if (block.timestamp + _motionDuration >= currentPeriodEnd) {
            return _payoutSum <= limit;
        } else {
            return _payoutSum <= limit - spent;
        }
    }

    function checkAndUpdateLimits(uint256 _payoutSum) external onlyRole(SET_LIMIT_PARAMETERS_ROLE) {
        _checkAndUpdateLimitParameters();
        _checkLimit(_payoutSum);
        _increaseSpent(_payoutSum);
    }

    /// @notice Returns current balance
    /// @return Balance of the budget
    function currentBudgetBalance() external view returns (uint256) {
        return limit - spent;
    }

    /// @notice Sets PeriodDurationMonth and limit
    /// @param _limit Limit to set
    /// @param _periodDurationMonth Period in months to set
    function setLimitParameters(uint256 _limit, uint256 _periodDurationMonth)
        external
        onlyRole(SET_LIMIT_PARAMETERS_ROLE)
    {
        _checkPeriodDurationMonth(_periodDurationMonth);
        periodDurationMonth = _periodDurationMonth;
        currentPeriodEnd = _getPeriodEndFromTimestamp(block.timestamp);
        limit = _limit;
    }

    /// @notice Returns limit and periodDurationMonth
    /// @return limit - the maximum that can be spent in a period
    /// @return periodDurationMonth - length of period in months
    function getLimitParameters() external view returns (uint256, uint256) {
        return (limit, periodDurationMonth);
    }

    /// @notice Returns amount spent in the current period, balance available for spending,
    /// @notice start date of the current period and end date of the current period
    /// @return amount spent in the current period
    /// @return balance available for spending in the current period
    /// @return start date of the current period
    /// @return end date of the current period
    function getCurrentPeriodState()
        external
        view
        returns (
            uint256,
            uint256,
            uint256,
            uint256
        )
    {
        return (
            spent,
            limit - spent,
            _getPeriodStartFromTimestamp(currentPeriodEnd - 1),
            currentPeriodEnd
        );
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _checkAndUpdateLimitParameters() internal {
        if (block.timestamp >= currentPeriodEnd) {
            currentPeriodEnd = _getPeriodEndFromTimestamp(block.timestamp);
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

    function _checkLimit(uint256 _payoutSum) internal view {
        require(_payoutSum <= limit - spent, ERROR_SUM_EXCEEDS_LIMIT);
    }

    function _increaseSpent(uint256 _payoutSum) internal {
        spent += _payoutSum;
    }

    function _getPeriodStartFromTimestamp(uint256 _timestamp) internal view returns (uint256) {
        (uint256 _year, uint256 _month, ) = BokkyPooBahsDateTimeLibrary.timestampToDate(_timestamp);
        return
            BokkyPooBahsDateTimeLibrary.timestampFromDate(
                _year,
                _month - ((_month - 1) % periodDurationMonth),
                1
            );
    }

    function _getPeriodEndFromTimestamp(uint256 _timestamp) internal view returns (uint256) {
        uint256 _periodStart = _getPeriodStartFromTimestamp(_timestamp);
        return BokkyPooBahsDateTimeLibrary.addMonths(_periodStart, periodDurationMonth);
    }
}
