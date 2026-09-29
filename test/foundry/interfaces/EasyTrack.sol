// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

// The subset of Easy Track the suite drives. The interface name matches the contract.

interface IEasyTrack {
    function createMotion(address _evmScriptFactory, bytes memory _evmScriptCallData)
        external
        returns (uint256);

    function enactMotion(uint256 _motionId, bytes memory _evmScriptCallData) external;

    function evmScriptExecutor() external view returns (address);

    function motionDuration() external view returns (uint256);
}
