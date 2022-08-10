// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity =0.8.6;

import "../LimitsChecker.sol";

contract LimitsCheckerWrapper is LimitsChecker {
    constructor(EasyTrack _easy_track) LimitsChecker(_easy_track) {}
}
