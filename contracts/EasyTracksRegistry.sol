// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./IEasyTrackExecutor.sol";

interface IForwardable {
    function forward(bytes memory _evmScript) external;
}

contract EasyTracksRegistry is Ownable {
    struct Motion {
        uint256 id;
        address executor;
        uint256 duration;
        uint256 startDate;
        uint256 snapshotBlock;
        uint256 objectionsThreshold;
        uint256 objectionsAmount;
        bytes data;
    }

    event MotionDurationChanged(uint256 _newDuration);
    event ObjectionsThresholdChanged(uint256 _newThreshold);
    event ExecutorAdded(
        address indexed _executor,
        bytes4 _executeMethodId,
        string _executeCalldataSignature,
        string _description
    );
    event ExecutorDeleted(address indexed _executor);
    event MotionCreated(uint256 indexed _motionId, address indexed _executor, bytes data);
    event MotionCanceled(uint256 indexed _motionId);

    string private constant ERROR_VALUE_TOO_SMALL = "VALUE_TOO_SMALL";
    string private constant ERROR_VALUE_TOO_LARGE = "VALUE_TOO_LARGE";
    string private constant ERROR_MOTION_NOT_FOUND = "MOTION_NOT_FOUND";
    string private constant ERROR_EXECUTOR_ALREADY_ADDED = "EXECUTOR_ALREADY_ADDED";
    string private constant ERROR_EXECUTOR_NOT_FOUND = "EXECUTOR_NOT_FOUND";
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

    address[] public executors;
    mapping(address => uint256) private executorIndices;

    uint256 private lastMotionId;
    Motion[] motions;
    mapping(uint256 => uint256) motionIndicesByMotionId;

    mapping(uint256 => mapping(address => bool)) objections;

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
        emit MotionDurationChanged(_motionDuration);
    }

    /**
     @notice Set percent of governance tokens required to reject a proposal.
     Can be callend only by owner of contract.
     */
    function setObjectionsThreshold(uint256 _objectionsThreshold) public onlyOwner {
        require(_objectionsThreshold <= MAX_OBJECTIONS_THRESHOLD, ERROR_VALUE_TOO_LARGE);
        objectionsThreshold = _objectionsThreshold;
        emit ObjectionsThresholdChanged(_objectionsThreshold);
    }

    /**
     @notice Adds a new `_executor` into the current list of executors.
     Can be callend only by owner of contract.
     */
    function addExecutor(address _executor) external onlyOwner {
        require(executorIndices[_executor] == 0, ERROR_EXECUTOR_ALREADY_ADDED);
        executors.push(_executor);
        executorIndices[_executor] = executors.length;
        IEasyTrackExecutor ex = IEasyTrackExecutor(_executor);
        emit ExecutorAdded(
            _executor,
            ex.executeMethodId(),
            ex.executeCalldataSignature(),
            ex.description()
        );
    }

    /**
     @notice Returns list of active executors
     */
    function getExecutors() public view returns (address[] memory result) {
        return executors;
    }

    function deleteExecutor(address _executor) external onlyOwner {
        uint256 index = _getExecutorIndex(_executor);
        uint256 lastIndex = executors.length - 1;

        if (index != lastIndex) {
            address lastExecutor = executors[lastIndex];
            executors[index] = lastExecutor;
            executorIndices[lastExecutor] = index + 1;
        }

        executors.pop();
        delete executorIndices[_executor];
        emit ExecutorDeleted(_executor);
    }

    function createMotion(address _executor, bytes memory _data)
        public
        executorExists(_executor)
        returns (uint256 _motionId)
    {
        IEasyTrackExecutor(_executor).beforeCreateMotionGuard(msg.sender, _data);

        Motion storage m = motions.push();
        _motionId = ++lastMotionId;

        m.id = _motionId;
        m.executor = _executor;
        m.duration = motionDuration;
        m.startDate = block.timestamp;
        m.snapshotBlock = block.number;
        m.objectionsThreshold = objectionsThreshold;
        m.data = _data;

        motionIndicesByMotionId[_motionId] = motions.length;

        emit MotionCreated(_motionId, _executor, _data);
    }

    function cancelMotion(uint256 _motionId, bytes memory _data) public motionExists(_motionId) {
        Motion storage m = motions[motionIndicesByMotionId[_motionId] - 1];

        IEasyTrackExecutor(m.executor).beforeCancelMotionGuard(msg.sender, _motionId, _data);

        _deleteMotion(_motionId);
        emit MotionCanceled(_motionId);
    }

    function getActiveMotions() public view returns (Motion[] memory res) {
        return motions;
    }

    function _deleteMotion(uint256 _motionId) private {
        uint256 index = motionIndicesByMotionId[_motionId] - 1;
        uint256 lastIndex = motions.length - 1;

        if (index != lastIndex) {
            Motion storage lastMotion = motions[lastIndex];
            motions[index] = lastMotion;
            motionIndicesByMotionId[lastMotion.id] = index + 1;
        }

        motions.pop();
        delete motionIndicesByMotionId[_motionId];
    }

    function _getExecutorIndex(address executorId) private view returns (uint256 _index) {
        _index = executorIndices[executorId];
        require(_index > 0, ERROR_EXECUTOR_NOT_FOUND);
        _index -= 1;
    }

    modifier executorExists(address _executor) {
        require(executorIndices[_executor] > 0, ERROR_EXECUTOR_NOT_FOUND);
        _;
    }

    modifier motionExists(uint256 _motionId) {
        require(motionIndicesByMotionId[_motionId] > 0, ERROR_MOTION_NOT_FOUND);
        _;
    }
}