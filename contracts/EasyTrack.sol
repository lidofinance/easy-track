// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "./MotionSettings.sol";
import "./EvmScriptExecutor.sol";
import "./EVMScriptFactoriesRegistry.sol";
import "./interfaces/IEVMScriptFactory.sol";

import "@openzeppelin/contracts/access/Ownable.sol";

interface IMiniMeToken {
    function balanceOfAt(address _owner, uint256 _blockNumber) external pure returns (uint256);

    function totalSupplyAt(uint256 _blockNumber) external view returns (uint256);
}

contract EasyTrack is Ownable, MotionSettings, EVMScriptFactoriesRegistry {
    event MotionCreated(
        uint256 indexed _motionId,
        address _creator,
        address indexed _evmScriptFactory,
        bytes _evmScriptCallData,
        bytes _evmScript
    );
    event MotionObjected(
        uint256 indexed _motionId,
        address indexed _objector,
        uint256 _weight,
        uint256 _votingPower
    );
    event MotionRejected(uint256 indexed _motionId);
    event MotionCanceled(uint256 indexed _motionId);
    event MotionEnacted(uint256 indexed _motionId);
    event EVMScriptExecutorChanged(address indexed _evmScriptExecutor);

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

    string private constant ERROR_ALREADY_OBJECTED = "ALREADY_OBJECTED";
    string private constant ERROR_NOT_ENOUGH_BALANCE = "NOT_ENOUGH_BALANCE";
    string private constant ERROR_NOT_CREATOR = "NOT_CREATOR";
    string private constant ERROR_MOTION_NOT_PASSED = "MOTION_NOT_PASSED";
    string private constant ERROR_UNEXPECTED_EVM_SCRIPT = "UNEXPECTED_EVM_SCRIPT";
    string private constant ERROR_MOTION_NOT_FOUND = "MOTION_NOT_FOUND";
    string private constant ERROR_MOTIONS_LIMIT_REACHED = "MOTIONS_LIMIT_REACHED";

    IMiniMeToken public governanceToken;
    EVMScriptExecutor public evmScriptExecutor;

    Motion[] public motions;
    uint256 private lastMotionId;
    mapping(uint256 => uint256) private motionIndicesByMotionId;
    mapping(uint256 => mapping(address => bool)) objections;

    constructor(address _governanceToken) {
        governanceToken = IMiniMeToken(_governanceToken);
    }

    function createMotion(address _evmScriptFactory, bytes memory _evmScriptCallData)
        external
        returns (uint256 _motionId)
    {
        bytes memory evmScript =
            _createEVMScript(_evmScriptFactory, msg.sender, _evmScriptCallData);
        require(motions.length < motionsCountLimit, ERROR_MOTIONS_LIMIT_REACHED);

        Motion storage m = motions.push();
        _motionId = ++lastMotionId;

        m.id = _motionId;
        m.creator = msg.sender;
        m.startDate = block.timestamp;
        m.snapshotBlock = block.number;

        m.duration = motionDuration;
        m.objectionsThreshold = objectionsThreshold;

        m.evmScriptCallData = _evmScriptCallData;
        m.evmScriptFactory = _evmScriptFactory;
        m.evmScriptHash = keccak256(evmScript);

        motionIndicesByMotionId[_motionId] = motions.length;

        emit MotionCreated(_motionId, msg.sender, _evmScriptFactory, _evmScriptCallData, evmScript);
    }

    function cancelMotion(uint256 _motionId) external {
        Motion storage m = _getMotion(_motionId);
        require(m.creator == msg.sender, ERROR_NOT_CREATOR);
        _deleteMotion(_motionId);
        emit MotionCanceled(_motionId);
    }

    function enactMotion(uint256 _motionId) external {
        Motion storage m = _getMotion(_motionId);
        require(m.startDate + m.duration <= block.timestamp, ERROR_MOTION_NOT_PASSED);

        bytes memory evmScript =
            _createEVMScript(m.evmScriptFactory, m.creator, m.evmScriptCallData);
        require(m.evmScriptHash == keccak256(evmScript), ERROR_UNEXPECTED_EVM_SCRIPT);

        evmScriptExecutor.executeEVMScript(evmScript);
        _deleteMotion(_motionId);
        emit MotionEnacted(_motionId);
    }

    function objectToMotion(uint256 _motionId) external {
        Motion storage m = _getMotion(_motionId);
        require(!objections[_motionId][msg.sender], ERROR_ALREADY_OBJECTED);
        objections[_motionId][msg.sender] = true;

        uint256 balance = governanceToken.balanceOfAt(msg.sender, m.snapshotBlock);
        require(balance > 0, ERROR_NOT_ENOUGH_BALANCE);

        m.objectionsAmount += balance;
        uint256 totalSupply = governanceToken.totalSupplyAt(m.snapshotBlock);
        m.objectionsAmountPct = (10000 * m.objectionsAmount) / totalSupply;

        emit MotionObjected(_motionId, msg.sender, balance, totalSupply);

        if (m.objectionsAmountPct > m.objectionsThreshold) {
            _deleteMotion(_motionId);
            emit MotionRejected(_motionId);
        }
    }

    function canObjectToMotion(uint256 _motionId, address _objector) external view returns (bool) {
        Motion storage m = _getMotion(_motionId);
        uint256 balance = governanceToken.balanceOfAt(_objector, m.snapshotBlock);
        return balance > 0 && !objections[_motionId][_objector];
    }

    function setEvmScriptExecutor(address _evmScriptExecutor) external onlyOwner {
        evmScriptExecutor = EVMScriptExecutor(_evmScriptExecutor);
    }

    function getMotions() external view returns (Motion[] memory) {
        return motions;
    }

    function _deleteMotion(uint256 _motionId) internal {
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

    function _getMotion(uint256 _motionId)
        internal
        view
        motionExists(_motionId)
        returns (Motion storage)
    {
        return motions[motionIndicesByMotionId[_motionId] - 1];
    }

    modifier motionExists(uint256 _motionId) {
        require(motionIndicesByMotionId[_motionId] > 0, ERROR_MOTION_NOT_FOUND);
        _;
    }
}
