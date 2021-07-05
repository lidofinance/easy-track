// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "./EasyTrackStorage.sol";

contract MotionSettings is EasyTrackStorage {
    string private constant ERROR_VALUE_TOO_SMALL = "VALUE_TOO_SMALL";
    string private constant ERROR_VALUE_TOO_LARGE = "VALUE_TOO_LARGE";

    /**
     @notice Sets duration of new created motions.
     Can be called only by the owner of contract.
     */
    function setMotionDuration(uint256 _motionDuration) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_motionDuration >= MIN_MOTION_DURATION, ERROR_VALUE_TOO_SMALL);
        motionDuration = _motionDuration;
        emit MotionDurationChanged(_motionDuration);
    }

    /**
     @notice Sets percent of governance tokens required to reject a proposal.
     Can be callend only by owner of contract.
     */
    function setObjectionsThreshold(uint256 _objectionsThreshold)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(_objectionsThreshold <= MAX_OBJECTIONS_THRESHOLD, ERROR_VALUE_TOO_LARGE);
        objectionsThreshold = _objectionsThreshold;
        emit ObjectionsThresholdChanged(_objectionsThreshold);
    }

    function setMotionsCountLimit(uint256 _motionsCountLimit)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(_motionsCountLimit < MAX_MOTIONS_LIMIT, ERROR_VALUE_TOO_LARGE);
        motionsCountLimit = _motionsCountLimit;
        emit MotionsCountLimitChanged(_motionsCountLimit);
    }
}
