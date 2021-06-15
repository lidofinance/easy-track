// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../EvmScriptExecutor.sol";

contract MotionsRegistryStub is EvmScriptExecutor {
    constructor() EvmScriptExecutor(address(0)) {}

    bool public createMotionCalled;
    bool public cancelMotionCalled;
    bool public enactMotionCalled;
    uint256 public cancelMotionId;
    uint256 public enactMotionId;
    bytes public motionData;
    bytes public evmScript;

    function createMotion(bytes memory _data) external returns (uint256 _motionId) {
        createMotionCalled = true;
        motionData = _data;
        return 1;
    }

    function cancelMotion(uint256 _motionId) external {
        cancelMotionCalled = true;
        cancelMotionId = _motionId;
    }

    function enactMotion(uint256 _motionId, bytes memory _evmScript) external {
        enactMotionCalled = true;
        enactMotionId = _motionId;
        evmScript = _evmScript;
    }

    function enactMotion(uint256 _motionId) external {
        enactMotionCalled = true;
        enactMotionId = _motionId;
    }

    function setMotionData(bytes memory _data) external {
        motionData = _data;
    }

    function getMotionData(uint256 _motionId) external view returns (bytes memory) {
        return motionData;
    }
}
