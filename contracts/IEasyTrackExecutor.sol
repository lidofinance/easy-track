// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

interface IEasyTrackExecutor {
    function description() external view returns (string memory);

    function executeCalldataSignature() external view returns (string memory);

    function executeMethodId() external view returns (bytes4);

    function beforeCreateMotionGuard(address _caller, bytes memory _data) external;

    function beforeCancelMotionGuard(
        address _caller,
        uint256 _motionId,
        bytes memory _data
    ) external;
}
