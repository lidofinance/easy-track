// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./libraries/EVMScriptCreator.sol";
import "./interfaces/IBokkyPooBahsDateTimeContract.sol";

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

/// @author zuzueeka
/// @notice Stores limits params and provides limit-enforcement logic
///
/// ▲ limit-spent (spendable balance)
/// |
/// │             |................              |..               limit-spent = limit-0 = limit
/// │.....        |                ...           |
/// │     ........|                   ......     |  ..............
///               |                         .....|
/// │─────────────────────────────────────────────────────────────> Time
/// |     ^       |                ^  ^     ^    |  ^               ^ - Motion enactment
/// │             |currentPeriodEndTimestamp     |currentPeriodEndTimestamp
/// |             |spent=0                       |spent=0
///
/// currentPeriodEndTimestamp is calculated as a calendar date of the beginning of
/// a next month, bi-months, quarter, half year, or year period.
/// If, for example, periodDurationMonths = 3, then it is considered that the date changes once a quarter.
/// And currentPeriodEndTimestamp can take values 1 Apr, 1 Jul, 1 Okt, 1 Jan.
/// If periodDurationMonths = 1, then shift of currentPeriodEndTimestamp occurs once a month
/// and currentPeriodEndTimestamp can take values 1 Feb, 1 Mar, 1 Apr etc
///
contract LimitsChecker is AccessControl {
    // -------------
    // EVENTS
    // -------------
    event LimitsParametersChanged(uint256 _limit, uint256 _periodDurationMonths);
    event SpendableAmountChanged(
        uint256 _alreadySpentAmount,
        uint256 _spendableAmount,
        uint256 indexed _periodStartTimestamp,
        uint256 _periodEndTimestamp
    );
    event CurrentPeriodAdvanced(uint256 _currentPeriodEndTimestamp);
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_INVALID_PERIOD_DURATION = "INVALID_PERIOD_DURATION";
    string private constant ERROR_SUM_EXCEEDS_SPENDABLE_BALANCE = "SUM_EXCEEDS_SPENDABLE_BALANCE";
    // -------------
    // ROLES
    // -------------
    bytes32 public constant SET_LIMIT_PARAMETERS_ROLE = keccak256("SET_LIMIT_PARAMETERS_ROLE");
    bytes32 public constant UPDATE_SPENDABLE_BALANCE_ROLE =
        keccak256("UPDATE_SPENDABLE_BALANCE_ROLE");

    // -------------
    // CONSTANTS
    // -------------

    // ------------
    // STORAGE VARIABLES
    // ------------

    /// @notice Address of BokkyPooBahsDateTimeContract
    IBokkyPooBahsDateTimeContract public immutable bokkyPooBahsDateTimeContract;

    /// @notice Length of period in months
    uint64 internal periodDurationMonths;

    /// @notice End of the current period
    uint128 internal currentPeriodEndTimestamp;

    /// @notice The maximum that can be spent in a period
    uint128 internal limit;

    /// @notice Amount already spent in the period
    uint128 internal spent;

    // ------------
    // CONSTRUCTOR
    // ------------
    constructor(
        address[] memory _setLimitParameterRoleHolders,
        address[] memory _updateLimitSpendingRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    ) {
        for (uint256 i = 0; i < _setLimitParameterRoleHolders.length; i++) {
            _setupRole(SET_LIMIT_PARAMETERS_ROLE, _setLimitParameterRoleHolders[i]);
        }
        for (uint256 i = 0; i < _updateLimitSpendingRoleHolders.length; i++) {
            _setupRole(UPDATE_SPENDABLE_BALANCE_ROLE, _updateLimitSpendingRoleHolders[i]);
        }
        bokkyPooBahsDateTimeContract = _bokkyPooBahsDateTimeContract;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Checks if _payoutAmount is less or equal than may be spent in the period
    /// @param _payoutAmount Motion total amount
    /// @param _motionDuration Motion duration - minimal time required to pass before enacting of motion
    /// @return True if _payoutAmount is less or equal than may be spent in the period
    function isUnderSpendableBalance(uint256 _payoutAmount, uint256 _motionDuration)
        external
        view
        returns (bool)
    {
        if (block.timestamp + _motionDuration >= currentPeriodEndTimestamp) {
            return _payoutAmount <= limit;
        } else {
            return _payoutAmount <= limit - spent;
        }
    }

    /// @notice Checks if _payoutAmount is less or equal than may be spent,
    /// @notice updates period if needed and increases the amount spent in the current period
    function updateSpendableBalance(uint256 _payoutAmount)
        external
        onlyRole(UPDATE_SPENDABLE_BALANCE_ROLE)
    {
        _checkPeriodDurationMonths(periodDurationMonths);

        /// At the moment when it is necessary to shift the currentPeriodEndTimestamp
        /// currentPeriodEndTimestamp takes on a new value and spent is set to zero. Thus begins a new period.
        if (block.timestamp >= currentPeriodEndTimestamp) {
            currentPeriodEndTimestamp = uint128(_getPeriodEndFromTimestamp(block.timestamp));
            spent = 0;
        }

        require(_payoutAmount <= limit - spent, ERROR_SUM_EXCEEDS_SPENDABLE_BALANCE);

        spent += uint128(_payoutAmount);

        (
            uint256 _alreadySpentAmount,
            uint256 _spendableAmount,
            uint256 _periodStartTimestamp,
            uint256 _periodEndTimestamp
        ) = this.getCurrentPeriodState();

        emit SpendableAmountChanged(
            _alreadySpentAmount,
            _spendableAmount,
            _periodStartTimestamp,
            _periodEndTimestamp
        );
    }

    /// @notice Returns balance that can be spent in the current period
    /// @return Balance that can be spent in the current period
    function currentSpendableBalance() external view returns (uint256) {
        return limit - spent;
    }

    /// @notice Sets periodDurationMonths and limit
    /// currentPeriodEndTimestamp will be calculated as a calendar date of the beginning of next month,
    /// bi-months, quarter, half year, or year period.
    /// @param _limit Limit to set
    /// @param _periodDurationMonths  Length of period in months to set.
    /// Duration of the period can be 1, 2, 3, 6 or 12 months.
    function setLimitParameters(uint256 _limit, uint256 _periodDurationMonths)
        external
        onlyRole(SET_LIMIT_PARAMETERS_ROLE)
    {
        _checkPeriodDurationMonths(_periodDurationMonths);
        periodDurationMonths = uint64(_periodDurationMonths);
        currentPeriodEndTimestamp = uint128(_getPeriodEndFromTimestamp(block.timestamp));
        limit = uint128(_limit);
        if (spent > limit) {
            spent = limit;
        }

        emit LimitsParametersChanged(_limit, _periodDurationMonths);
    }

    /// @notice Returns limit and periodDurationMonths
    /// @return limit - the maximum that can be spent in a period
    /// @return periodDurationMonths - length of period in months
    function getLimitParameters() external view returns (uint256, uint256) {
        return (limit, periodDurationMonths);
    }

    /// @notice Returns amount spent in the current period, balance available for spending,
    /// @notice start date of the current period and end date of the current period
    /// @return _alreadySpentAmount - amount spent in the current period
    /// @return _spendableAmount - balance available for spending in the current period
    /// @return _periodStartTimestamp - start date of the current period
    /// @return _periodEndTimestamp - end date of the current period
    function getCurrentPeriodState()
        external
        view
        returns (
            uint256 _alreadySpentAmount,
            uint256 _spendableAmount,
            uint256 _periodStartTimestamp,
            uint256 _periodEndTimestamp
        )
    {
        return (
            spent,
            limit - spent,
            _getPeriodStartFromTimestamp(currentPeriodEndTimestamp - 1),
            currentPeriodEndTimestamp
        );
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------
    function _checkPeriodDurationMonths(uint256 _periodDurationMonths) internal view {
        require(
            _periodDurationMonths == 1 ||
                _periodDurationMonths == 2 ||
                _periodDurationMonths == 3 ||
                _periodDurationMonths == 6 ||
                _periodDurationMonths == 12,
            ERROR_INVALID_PERIOD_DURATION
        );
    }

    function _getPeriodStartFromTimestamp(uint256 _timestamp) internal view returns (uint256) {
        // Get year and number of month of the timestamp:
        (uint256 _year, uint256 _month, ) = bokkyPooBahsDateTimeContract.timestampToDate(
            _timestamp
        );
        // We assume that the year will remain the same,
        // because the beginning of the current calendar period will necessarily be in the same year.
        uint256 _periodStartYear = _year;
        // Get the number of the start date month:
        uint256 _periodStartMonth = _getFirstMonthInPeriodFromCurrentMonth(_month);
        // The beginning of the period always matches the calendar date of the beginning of the month.
        uint256 _periodStartDay = 1;
        return
            bokkyPooBahsDateTimeContract.timestampFromDate(
                _periodStartYear,
                _periodStartMonth,
                _periodStartDay
            );
    }

    function _getFirstMonthInPeriodFromCurrentMonth(uint256 _month)
        internal
        view
        returns (uint256 _firstMonthInPeriod)
    {
        // To get the number of the first month in the period:
        //   1. get the number of the period:
        uint256 _periodNumber = (_month - 1) / periodDurationMonths;
        //   2. and then the number of the first month in this period:
        _firstMonthInPeriod = _periodNumber * periodDurationMonths + 1;
        // The shift by - 1 and then by + 1 happens because the months in the calendar start from 1 and not from 0.
    }

    function _getPeriodEndFromTimestamp(uint256 _timestamp) internal view returns (uint256) {
        uint256 _periodStart = _getPeriodStartFromTimestamp(_timestamp);
        return bokkyPooBahsDateTimeContract.addMonths(_periodStart, periodDurationMonths);
    }
}
