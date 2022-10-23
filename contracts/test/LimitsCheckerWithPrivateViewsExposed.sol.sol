// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity =0.8.6;

import "../LimitsChecker.sol";
import "../interfaces/IBokkyPooBahsDateTimeContract.sol";
import "../EasyTrack.sol";

contract LimitsCheckerWithPrivateViewsExposed is LimitsChecker {
    constructor(
        address[] memory _setLimitParametersRoleHolders,
        address[] memory _updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    )
        LimitsChecker(
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        )
    {}

    function getFirstMonthInPeriodFromCurrentMonth(uint256 _month)
        public
        view
        returns (uint256 _firstMonthInPeriod)
    {
        _firstMonthInPeriod = _getFirstMonthInPeriodFromMonth(_month, periodDurationMonths);
    }

    function getPeriodStartFromTimestamp(uint256 _timestamp) public view returns (uint256) {
        return _getPeriodStartFromTimestamp(_timestamp);
    }

    function getPeriodEndFromTimestamp(uint256 _timestamp) public view returns (uint256) {
        return _getPeriodEndFromTimestamp(_timestamp);
    }
}
