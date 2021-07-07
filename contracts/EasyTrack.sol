// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./MotionSettings.sol";
import "./EVMScriptFactoriesRegistry.sol";

import "./interfaces/IEVMScriptExecutor.sol";

import "OpenZeppelin/openzeppelin-contracts@4.1.0/contracts/proxy/utils/UUPSUpgradeable.sol";

contract EasyTrack is UUPSUpgradeable, MotionSettings, EVMScriptFactoriesRegistry {
    // -------------
    // EVENTS
    // -------------
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

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_ALREADY_OBJECTED = "ALREADY_OBJECTED";
    string private constant ERROR_NOT_ENOUGH_BALANCE = "NOT_ENOUGH_BALANCE";
    string private constant ERROR_NOT_CREATOR = "NOT_CREATOR";
    string private constant ERROR_MOTION_NOT_PASSED = "MOTION_NOT_PASSED";
    string private constant ERROR_UNEXPECTED_EVM_SCRIPT = "UNEXPECTED_EVM_SCRIPT";
    string private constant ERROR_MOTION_NOT_FOUND = "MOTION_NOT_FOUND";
    string private constant ERROR_MOTIONS_LIMIT_REACHED = "MOTIONS_LIMIT_REACHED";

    // ------------------
    // PUBLIC METHODS
    // ------------------
    function createMotion(address _evmScriptFactory, bytes memory _evmScriptCallData)
        external
        whenNotPaused
        returns (uint256 _newMotionId)
    {
        bytes memory evmScript =
            _createEVMScript(_evmScriptFactory, msg.sender, _evmScriptCallData);
        require(motions.length < motionsCountLimit, ERROR_MOTIONS_LIMIT_REACHED);

        Motion storage newMotion = motions.push();
        _newMotionId = ++lastMotionId;

        newMotion.id = _newMotionId;
        newMotion.creator = msg.sender;
        newMotion.startDate = block.timestamp;
        newMotion.snapshotBlock = block.number;

        newMotion.duration = motionDuration;
        newMotion.objectionsThreshold = objectionsThreshold;

        newMotion.evmScriptFactory = _evmScriptFactory;
        newMotion.evmScriptHash = keccak256(evmScript);

        motionIndicesByMotionId[_newMotionId] = motions.length;

        emit MotionCreated(
            _newMotionId,
            msg.sender,
            _evmScriptFactory,
            _evmScriptCallData,
            evmScript
        );
    }

    function enactMotion(uint256 _motionId, bytes memory _evmScriptCallData)
        external
        whenNotPaused
    {
        Motion storage motion = _getMotion(_motionId);
        require(motion.startDate + motion.duration <= block.timestamp, ERROR_MOTION_NOT_PASSED);

        bytes memory evmScript =
            _createEVMScript(motion.evmScriptFactory, motion.creator, _evmScriptCallData);

        require(motion.evmScriptHash == keccak256(evmScript), ERROR_UNEXPECTED_EVM_SCRIPT);

        evmScriptExecutor.executeEVMScript(evmScript);
        _deleteMotion(_motionId);
        emit MotionEnacted(_motionId);
    }

    function objectToMotion(uint256 _motionId) external {
        Motion storage motion = _getMotion(_motionId);
        require(!objections[_motionId][msg.sender], ERROR_ALREADY_OBJECTED);
        objections[_motionId][msg.sender] = true;

        uint256 balance = governanceToken.balanceOfAt(msg.sender, motion.snapshotBlock);
        require(balance > 0, ERROR_NOT_ENOUGH_BALANCE);

        motion.objectionsAmount += balance;
        uint256 totalSupply = governanceToken.totalSupplyAt(motion.snapshotBlock);
        motion.objectionsAmountPct = (10000 * motion.objectionsAmount) / totalSupply;

        emit MotionObjected(_motionId, msg.sender, balance, totalSupply);

        if (motion.objectionsAmountPct > motion.objectionsThreshold) {
            _deleteMotion(_motionId);
            emit MotionRejected(_motionId);
        }
    }

    function cancelMotion(uint256 _motionId) external {
        Motion storage motion = _getMotion(_motionId);
        require(motion.creator == msg.sender, ERROR_NOT_CREATOR);
        _deleteMotion(_motionId);
        emit MotionCanceled(_motionId);
    }

    function cancelMotions(uint256[] memory _motionIds) external onlyRole(CANCEL_ROLE) {
        for (uint256 i = 0; i < _motionIds.length; ++i) {
            if (motionIndicesByMotionId[_motionIds[i]] > 0) {
                _deleteMotion(_motionIds[i]);
                emit MotionCanceled(_motionIds[i]);
            }
        }
    }

    function cancelAllMotions() external onlyRole(CANCEL_ROLE) {
        uint256 motionsCount = motions.length;
        while (motionsCount > 0) {
            motionsCount -= 1;
            uint256 motionId = motions[motionsCount].id;
            _deleteMotion(motionId);
            emit MotionCanceled(motionId);
        }
    }

    function setEVMScriptExecutor(address _evmScriptExecutor)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        evmScriptExecutor = IEVMScriptExecutor(_evmScriptExecutor);
        emit EVMScriptExecutorChanged(_evmScriptExecutor);
    }

    function pause() external whenNotPaused onlyRole(PAUSE_ROLE) {
        _pause();
    }

    function unpause() external whenPaused onlyRole(UNPAUSE_ROLE) {
        _unpause();
    }

    // ----------
    // VIEWS
    // ----------
    function canObjectToMotion(uint256 _motionId, address _objector) external view returns (bool) {
        Motion storage motion = _getMotion(_motionId);
        uint256 balance = governanceToken.balanceOfAt(_objector, motion.snapshotBlock);
        return balance > 0 && !objections[_motionId][_objector];
    }

    function getMotions() external view returns (Motion[] memory) {
        return motions;
    }

    function getMotion(uint256 _motionId) external view returns (Motion memory) {
        return _getMotion(_motionId);
    }

    // -------
    // PRIVATE METHODS
    // -------

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

    function _getMotion(uint256 _motionId)
        private
        view
        motionExists(_motionId)
        returns (Motion storage)
    {
        return motions[motionIndicesByMotionId[_motionId] - 1];
    }

    function _authorizeUpgrade(address newImplementation)
        internal
        override
        onlyRole(DEFAULT_ADMIN_ROLE)
    {}

    modifier motionExists(uint256 _motionId) {
        require(motionIndicesByMotionId[_motionId] > 0, ERROR_MOTION_NOT_FOUND);
        _;
    }
}
