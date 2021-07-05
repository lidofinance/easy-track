// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "./interfaces/IEVMScriptExecutor.sol";

import "OpenZeppelin/openzeppelin-contracts-upgradeable@4.1.0/contracts/access/AccessControlUpgradeable.sol";
import "OpenZeppelin/openzeppelin-contracts-upgradeable@4.1.0/contracts/security/PausableUpgradeable.sol";

interface IMiniMeToken {
    function balanceOfAt(address _owner, uint256 _blockNumber) external pure returns (uint256);

    function totalSupplyAt(uint256 _blockNumber) external view returns (uint256);
}

struct Motion {
    uint256 id;
    address evmScriptFactory;
    address creator;
    uint256 duration;
    uint256 startDate;
    uint256 snapshotBlock;
    uint256 objectionsThreshold;
    uint256 objectionsAmount;
    uint256 objectionsAmountPct;
    bytes32 evmScriptHash;
}

contract EasyTrackStorage is Initializable, PausableUpgradeable, AccessControlUpgradeable {
    // -------------
    // EVENTS
    // -------------
    event MotionDurationChanged(uint256 _motionDuration);
    event MotionsCountLimitChanged(uint256 _newMotionsCountLimit);
    event ObjectionsThresholdChanged(uint256 _newThreshold);

    // -------------
    // ROLES
    // -------------

    bytes32 public constant PAUSE_ROLE = keccak256("PAUSE_ROLE");
    bytes32 public constant UNPAUSE_ROLE = keccak256("UNPAUSE_ROLE");
    bytes32 public constant CANCEL_ROLE = keccak256("CANCEL_ROLE");

    // ------------
    // CONSTANTS
    // ------------

    /// @dev upper bound for motionsCountLimit value.
    uint256 public constant MAX_MOTIONS_LIMIT = 24;

    /// @dev upper bound for objectionsThreshold value.
    /// Stored in basis points (1% = 100)
    uint256 public constant MAX_OBJECTIONS_THRESHOLD = 500;

    /// @dev lower bound for motionDuration value
    uint256 public constant MIN_MOTION_DURATION = 48 hours;

    // ------------
    // MOTION SETTING VARIABLES
    // ------------
    uint256 public objectionsThreshold;
    uint256 public motionsCountLimit;
    uint256 public motionDuration;

    // ------------
    // EVM SCRIPT FACTORIES VARIABLES
    // ------------
    address[] public evmScriptFactories;
    mapping(address => uint256) internal evmScriptFactoryIndices;
    mapping(address => bytes) public evmScriptFactoryPermissions;

    // ------------
    // EASY TRACK VARIABLES
    // ------------
    Motion[] public motions;
    uint256 internal lastMotionId;
    IMiniMeToken public governanceToken;
    IEVMScriptExecutor public evmScriptExecutor;
    mapping(uint256 => uint256) internal motionIndicesByMotionId;
    mapping(uint256 => mapping(address => bool)) public objections;

    function __EasyTrackStorage_init(address _governanceToken, address _admin) public initializer {
        __Pausable_init();
        __AccessControl_init();
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        _setupRole(PAUSE_ROLE, _admin);
        _setupRole(UNPAUSE_ROLE, _admin);
        _setupRole(CANCEL_ROLE, _admin);

        objectionsThreshold = 50;
        motionsCountLimit = MAX_MOTIONS_LIMIT;
        motionDuration = MIN_MOTION_DURATION;
        governanceToken = IMiniMeToken(_governanceToken);

        emit MotionDurationChanged(MIN_MOTION_DURATION);
        emit MotionsCountLimitChanged(MAX_MOTIONS_LIMIT);
        emit ObjectionsThresholdChanged(50);
    }
}
