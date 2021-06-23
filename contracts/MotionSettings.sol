// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/access/Ownable.sol";

contract MotionSettings is Ownable {
    event MotionDurationChanged(uint256 _motionDuration);
    event MotionsCountLimitChanged(uint256 _newMotionsCountLimit);
    event ObjectionsThresholdChanged(uint256 _newThreshold);

    string private constant ERROR_VALUE_TOO_SMALL = "VALUE_TOO_SMALL";
    string private constant ERROR_VALUE_TOO_LARGE = "VALUE_TOO_LARGE";

    uint256 public constant MAX_MOTIONS_LIMIT = 100;
    /**
     @dev upper bound for objectionsThreshold value.
     Stored in basis points (1% = 100)
     */
    uint64 public constant MAX_OBJECTIONS_THRESHOLD = 500;

    /**
     @dev lower bound for motionDuration value
     */
    uint64 public constant MIN_MOTION_DURATION = 48 hours;

    uint256 public objectionsThreshold = 50;
    uint256 public motionsCountLimit = MAX_MOTIONS_LIMIT;
    uint256 public motionDuration = MIN_MOTION_DURATION;

    /**
     @notice Set duration of new created motions.
     Can be called only by the owner of contract.
     */
    function setMotionDuration(uint256 _motionDuration) external onlyOwner {
        require(_motionDuration >= MIN_MOTION_DURATION, ERROR_VALUE_TOO_SMALL);
        motionDuration = uint64(_motionDuration);
        emit MotionDurationChanged(_motionDuration);
    }

    /**
     @notice Set percent of governance tokens required to reject a proposal.
     Can be callend only by owner of contract.
     */
    function setObjectionsThreshold(uint256 _objectionsThreshold) external onlyOwner {
        require(_objectionsThreshold <= MAX_OBJECTIONS_THRESHOLD, ERROR_VALUE_TOO_LARGE);
        objectionsThreshold = _objectionsThreshold;
        emit ObjectionsThresholdChanged(_objectionsThreshold);
    }

    function setMotionsCountLimit(uint256 _motionsCountLimit) external onlyOwner {
        require(_motionsCountLimit < MAX_MOTIONS_LIMIT, ERROR_VALUE_TOO_LARGE);
        motionsCountLimit = _motionsCountLimit;
        emit MotionsCountLimitChanged(_motionsCountLimit);
    }
}
