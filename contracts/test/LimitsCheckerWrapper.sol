// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity =0.8.6;

import "../LimitsChecker.sol";
import "../interfaces/IBokkyPooBahsDateTimeContract.sol";
import "../EasyTrack.sol";

contract LimitsCheckerWrapper is LimitsChecker {
    constructor(
        address[] memory _setLimitParametersRoleHolders,
        address[] memory _updateLimitSpendingsRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    )
        LimitsChecker(
            _setLimitParametersRoleHolders,
            _updateLimitSpendingsRoleHolders,
            _bokkyPooBahsDateTimeContract
        )
    {}
}
