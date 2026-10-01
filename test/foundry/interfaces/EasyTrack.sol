// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

// Core Easy Track contracts (subset used by the suite; interface names match the contracts).

interface IEVMScriptFactory {
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        returns (bytes memory);
}

interface IEasyTrack {
    function createMotion(address _evmScriptFactory, bytes memory _evmScriptCallData)
        external
        returns (uint256);

    function enactMotion(uint256 _motionId, bytes memory _evmScriptCallData) external;

    function isEVMScriptFactory(address _maybeEVMScriptFactory) external view returns (bool);

    function evmScriptFactoryPermissions(address _evmScriptFactory) external view returns (bytes memory);

    function evmScriptExecutor() external view returns (address);

    function motionDuration() external view returns (uint256);
}
