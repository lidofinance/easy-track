// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Ports of `tests/constants.py`
library Constants {
    uint256 internal constant MAX_MOTIONS_LIMIT = 24;
    uint256 internal constant MAX_OBJECTIONS_THRESHOLD = 500;
    uint256 internal constant MIN_MOTION_DURATION = 48 * 60 * 60;
    uint256 internal constant DEFAULT_OBJECTIONS_THRESHOLD = 50;
}
