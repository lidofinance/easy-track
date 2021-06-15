// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "./EvmScriptExecutor.sol";
import "./EasyTracksRegistry.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IMiniMeToken {
    function balanceOfAt(address _owner, uint256 _blockNumber) external pure returns (uint256);

    function totalSupplyAt(uint256 _blockNumber) external view returns (uint256);
}

/// Stores all created motions
/// and contains logic to create/cancel motions which
/// might be done only by EasyTrack contracts registered in the EasyTracksRegistry
/// Allows object motions for GovernanceToken holders
/// Has permissions to forward to Aragon agent
contract MotionsRegistry is Ownable, EvmScriptExecutor {
    event MotionDurationChanged(uint256 _motionDuration);
    event ObjectionSent(
        uint256 indexed _motionId,
        address indexed _voterAddress,
        uint256 _weight,
        uint256 _votingPower
    );
    event MotionRejected(uint256 indexed _motionId);
    event MotionCanceled(uint256 indexed _motionId);
    event MotionCreated(uint256 indexed _motionId, address indexed _easyTrack, bytes _data);
    event MotionEnacted(uint256 indexed _motionId);
    event MotionsCountLimitChanged(uint256 _newMotionsCountLimit);
    event ObjectionsThresholdChanged(uint256 _newThreshold);

    string private constant ERROR_ALREADY_OBJECTED = "ALREADY_OBJECTED";
    string private constant ERROR_MOTION_PASSED = "MOTION_PASSED";
    string private constant ERROR_NOT_ENOUGH_BALANCE = "NOT_ENOUGH_BALANCE";
    string private constant ERROR_MOTIONS_LIMIT_REACHED = "MOTIONS_LIMIT_REACHED";
    string private constant ERROR_MOTION_NOT_FOUND = "MOTION_NOT_FOUND";
    string private constant ERROR_VALUE_TOO_SMALL = "VALUE_TOO_SMALL";
    string private constant ERROR_VALUE_TOO_LARGE = "VALUE_TOO_LARGE";
    string private constant ERROR_WRONG_EASYTRACK = "WRONG_EASYTRACK";
    string private constant ERROR_NOT_EASY_TRACK = "NOT_EASY_TRACK";
    string private constant ERROR_MOTION_NOT_PASSED = "MOTION_NOT_PASSED";

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

    struct Motion {
        uint256 id;
        address easyTrack;
        uint256 duration;
        uint256 startDate;
        uint256 snapshotBlock;
        uint256 objectionsThreshold;
        uint256 objectionsAmount;
        uint256 objectionsAmountPct;
        bytes data;
    }

    Motion[] public motions;
    uint256 private lastMotionId;
    mapping(uint256 => uint256) private motionIndicesByMotionId;

    IMiniMeToken public governanceToken;

    mapping(uint256 => mapping(address => bool)) objections;
    /**
     @dev Percent of governance tokens required to reject a proposal
     values stored in basis points (1% = 100).
     Default value is 0.5%
     */
    uint256 public objectionsThreshold = 50;
    uint256 public motionsCountLimit = MAX_MOTIONS_LIMIT;
    uint256 public motionDuration = MIN_MOTION_DURATION;

    EasyTracksRegistry public easyTracksRegistry;

    constructor(
        address _easytracksRegistry,
        address _governanceToken,
        address _aragonAgent
    ) EvmScriptExecutor(_aragonAgent) {
        governanceToken = IMiniMeToken(_governanceToken);
        easyTracksRegistry = EasyTracksRegistry(_easytracksRegistry);
    }

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

    function createMotion(bytes memory _data) external onlyEasyTrack returns (uint256 _motionId) {
        require(motions.length < motionsCountLimit, ERROR_MOTIONS_LIMIT_REACHED);

        Motion storage m = motions.push();
        _motionId = ++lastMotionId;

        m.id = _motionId;
        m.easyTrack = msg.sender;
        m.duration = motionDuration;
        m.startDate = block.timestamp;
        m.snapshotBlock = block.number;
        m.objectionsThreshold = objectionsThreshold;
        m.data = _data;

        motionIndicesByMotionId[_motionId] = motions.length;

        emit MotionCreated(_motionId, msg.sender, _data);
    }

    function cancelMotion(uint256 _motionId) external onlyEasyTrack motionExists(_motionId) {
        Motion storage m = _getMotion(_motionId);
        require(m.easyTrack == msg.sender, ERROR_WRONG_EASYTRACK);
        _deleteMotion(_motionId);
        emit MotionCanceled(_motionId);
    }

    // validates called by easytrack
    // and m.easytrack == msg.sender (allow delete only motions with same type)
    function enactMotion(uint256 _motionId, bytes memory _evmScript) external {
        _enactMotion(_motionId, _evmScript);
    }

    function enactMotion(uint256 _motionId) external {
        _enactMotion(_motionId, hex"");
    }

    function objectToMotion(uint256 _motionId) external motionExists(_motionId) {
        require(!objections[_motionId][msg.sender], ERROR_ALREADY_OBJECTED);
        objections[_motionId][msg.sender] = true;

        Motion storage m = _getMotion(_motionId);

        require(m.startDate + m.duration > block.timestamp, ERROR_MOTION_PASSED);

        uint256 balance = governanceToken.balanceOfAt(msg.sender, m.snapshotBlock);
        require(balance > 0, ERROR_NOT_ENOUGH_BALANCE);

        m.objectionsAmount += balance;
        uint256 totalSupply = governanceToken.totalSupplyAt(m.snapshotBlock);
        m.objectionsAmountPct = (10000 * m.objectionsAmount) / totalSupply;

        emit ObjectionSent(_motionId, msg.sender, balance, totalSupply);

        if (m.objectionsAmountPct > m.objectionsThreshold) {
            _deleteMotion(_motionId);
            emit MotionRejected(_motionId);
        }
    }

    function getMotions() external view returns (Motion[] memory) {
        return motions;
    }

    function getMotionData(uint256 _motionId)
        external
        view
        motionExists(_motionId)
        returns (bytes memory)
    {
        Motion storage m = _getMotion(_motionId);
        return m.data;
    }

    function canObjectToMotion(uint256 _motionId, address _objector)
        external
        view
        motionExists(_motionId)
        returns (bool)
    {
        Motion storage m = _getMotion(_motionId);
        uint256 balance = governanceToken.balanceOfAt(_objector, m.snapshotBlock);
        return balance > 0 && !objections[_motionId][_objector];
    }

    function _enactMotion(uint256 _motionId, bytes memory _evmScript)
        internal
        onlyEasyTrack
        motionExists(_motionId)
    {
        Motion storage m = _getMotion(_motionId);
        require(m.easyTrack == msg.sender, ERROR_WRONG_EASYTRACK);
        require(m.startDate + m.duration <= block.timestamp, ERROR_MOTION_NOT_PASSED);
        _deleteMotion(_motionId);
        if (_evmScript.length > 0) {
            executeScript(_evmScript);
        }
        emit MotionEnacted(_motionId);
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

    function _getMotion(uint256 _motionId) private view returns (Motion storage) {
        return motions[motionIndicesByMotionId[_motionId] - 1];
    }

    modifier motionExists(uint256 _motionId) {
        require(motionIndicesByMotionId[_motionId] > 0, ERROR_MOTION_NOT_FOUND);
        _;
    }

    modifier onlyEasyTrack {
        require(easyTracksRegistry.isEasyTrack(msg.sender), ERROR_NOT_EASY_TRACK);
        _;
    }
}
