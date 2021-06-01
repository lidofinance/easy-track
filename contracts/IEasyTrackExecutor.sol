// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

interface IEasyTrackExecutor {
    function beforeCreateMotionGuard(address _caller, bytes memory _data) external;

    function beforeCancelMotionGuard(
        address _caller,
        bytes memory _motionData,
        bytes memory _cancelData
    ) external;

    function execute(bytes memory _motionData, bytes memory _enactData) external;
}
