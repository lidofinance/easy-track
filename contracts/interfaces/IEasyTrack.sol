// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

interface IEasyTrack {
    function motionDuration() external view returns (uint256);
    function evmScriptExecutor() external view returns (address);
}