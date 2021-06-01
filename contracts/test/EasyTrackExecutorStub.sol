// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../EasyTrackExecutor.sol";

contract EasyTrackExecutorStub is EasyTrackExecutor {
    struct BeforeCreateCallData {
        bool isCalled;
        address _caller;
        bytes _data;
    }

    struct BeforeCancelCallData {
        bool isCalled;
        address _caller;
        bytes _motionData;
        bytes _cancelData;
    }

    struct ExecuteCallData {
        bool isCalled;
        bytes motionData;
        bytes enactData;
    }

    BeforeCreateCallData public beforeCreateGuardCallData;
    BeforeCancelCallData public beforeCancelGuardCallData;
    ExecuteCallData public executeCallData;

    constructor(address _easyTraksRegistry) EasyTrackExecutor(_easyTraksRegistry) {}

    function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal override {
        beforeCreateGuardCallData = BeforeCreateCallData(true, _caller, _data);
    }

    function _beforeCancelMotionGuard(
        address _caller,
        bytes memory _motionData,
        bytes memory _cancelData
    ) internal override {
        beforeCancelGuardCallData = BeforeCancelCallData(true, _caller, _motionData, _cancelData);
    }

    function execute(bytes calldata _motionData, bytes calldata _enactData) external override {
        executeCallData = ExecuteCallData(true, _motionData, _enactData);
    }
}
