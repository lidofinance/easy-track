// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import "./interfaces/IEVMScriptExecutor.sol";

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
    bytes evmScriptCallData;
}

contract MotionSettingsStorage is Initializable {
    event MotionDurationChanged(uint256 _motionDuration);
    event MotionsCountLimitChanged(uint256 _newMotionsCountLimit);
    event ObjectionsThresholdChanged(uint256 _newThreshold);

    uint256 public constant MAX_MOTIONS_LIMIT = 24;
    /**
     @dev upper bound for objectionsThreshold value.
     Stored in basis points (1% = 100)
     */
    uint64 public constant MAX_OBJECTIONS_THRESHOLD = 500;

    /**
     @dev lower bound for motionDuration value
     */
    uint64 public constant MIN_MOTION_DURATION = 48 hours;

    uint256 public objectionsThreshold;
    uint256 public motionsCountLimit;
    uint256 public motionDuration;

    function __MotionsStorage_init() internal virtual initializer {
        objectionsThreshold = 50;
        motionsCountLimit = MAX_MOTIONS_LIMIT;
        motionDuration = MIN_MOTION_DURATION;

        emit MotionDurationChanged(MIN_MOTION_DURATION);
        emit MotionsCountLimitChanged(MAX_MOTIONS_LIMIT);
        emit ObjectionsThresholdChanged(50);
    }
}

contract EVMScriptFactoriesStorage {
    address[] public evmScriptFactories;
    mapping(address => uint256) internal evmScriptFactoryIndices;
    mapping(address => bytes) public evmScriptFactoryPermissions;
}

contract EasyTrackStorage is Initializable, MotionSettingsStorage, EVMScriptFactoriesStorage {
    Motion[] public motions;
    uint256 internal lastMotionId;

    IMiniMeToken public governanceToken;
    IEVMScriptExecutor public evmScriptExecutor;

    mapping(uint256 => uint256) internal motionIndicesByMotionId;
    mapping(uint256 => mapping(address => bool)) objections;

    function __EasyTrackStorage_init() public virtual initializer {
        MotionSettingsStorage.__MotionsStorage_init();
    }
}
