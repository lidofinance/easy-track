// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./IEasyTrackExecutor.sol";

interface IForwardable {
    function forward(bytes memory _evmScript) external;
}

contract EasyTracksRegistry is Ownable {
    struct MotionExecutor {
        uint256 id;
        IEasyTrackExecutor executorAddress;
    }
    string private constant ERROR_VALUE_TOO_SMALL = "VALUE_TOO_SMALL";
    string private constant ERROR_VALUE_TOO_LARGE = "VALUE_TOO_LARGE";

    /**
     @dev upper bound for objectionsThreshold value.
     Stored in basis points (1% = 100)
     */
    uint64 private constant MAX_OBJECTIONS_THRESHOLD = 500;

    /**
     @dev lower bound for motionDuration value
     */
    uint64 private constant MIN_MOTION_DURATION = 48 hours;

    /**
     @dev Aragon agent where evm script will be forwarded to
     */
    IForwardable public aragonAgent;

    /**
     @dev Duration of the new motions in seconds
     */
    uint256 public motionDuration = MIN_MOTION_DURATION;

    /**
     @dev Percent of governance tokens required to reject a proposal
     values stored in basis points (1% = 100).
     Default value is 0.5%
     */
    uint256 public objectionsThreshold = 50;

    /**
     @dev Id of last created executor
     */
    uint256 private lastExecutorId;

    /**
     @dev List of active executors
     */
    uint256[] private executorIds;

    /**
     @dev Executors by id
     */
    mapping(uint256 => IEasyTrackExecutor) private executors;

    constructor(address _aragonAgent) {
        aragonAgent = IForwardable(_aragonAgent);
    }

    /**
     @notice Set duration of new created motions.
     Can be called only by the owner of contract.
     */
    function setMotionDuration(uint256 _motionDuration) public onlyOwner {
        require(_motionDuration >= MIN_MOTION_DURATION, ERROR_VALUE_TOO_SMALL);
        motionDuration = uint64(_motionDuration);
    }

    /**
     @notice Set percent of governance tokens required to reject a proposal.
     Can be callend only by owner of contract.
     */
    function setObjectionsThreshold(uint256 _objectionsThreshold) public onlyOwner {
        require(_objectionsThreshold <= MAX_OBJECTIONS_THRESHOLD, ERROR_VALUE_TOO_LARGE);
        objectionsThreshold = _objectionsThreshold;
    }

    /**
     @notice Adds a new `_executor` into the current list of executors.
     Can be callend only by owner of contract.
     */
    function addMotionExecutor(address _executor) external onlyOwner {
        uint256 id = ++lastExecutorId;
        executorIds.push(id);
        executors[id] = IEasyTrackExecutor(_executor);
    }

    /**
     @notice Returns list of active executors
     */
    function getMotionExecutors() public view returns (MotionExecutor[] memory result) {
        uint256 count = executorIds.length;
        result = new MotionExecutor[](count);
        for (uint256 i = 0; i < count; i++) {
            uint256 id = executorIds[i];
            result[i] = MotionExecutor(id, executors[id]);
        }
    }
}
