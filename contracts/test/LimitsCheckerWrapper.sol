// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity =0.8.6;

import "../LimitsChecker.sol";
import "../interfaces/IBokkyPooBahsDateTimeContract.sol";
import "../EasyTrack.sol";

contract LimitsCheckerWrapper is LimitsChecker {

    constructor(
        EasyTrack _easyTrack,
        address[] memory _setLimitParametersRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    ) LimitsChecker(_easyTrack, _setLimitParametersRoleHolders, _bokkyPooBahsDateTimeContract)
    {
    }

}
