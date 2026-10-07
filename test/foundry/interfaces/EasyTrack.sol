// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

// The subset of Easy Track and its reward programs registry the suite drives. The interface names
// match the contracts.

interface IEasyTrack {
    /// @dev `EasyTrack.Motion`
    struct Motion {
        uint256 id;
        address evmScriptFactory;
        address creator;
        uint256 duration;
        uint256 startDate;
        uint256 snapshotBlock;
        uint256 objectionsThreshold;
        uint256 objectionsAmount;
        bytes32 evmScriptHash;
    }

    function createMotion(address _evmScriptFactory, bytes memory _evmScriptCallData)
        external
        returns (uint256);

    function enactMotion(uint256 _motionId, bytes memory _evmScriptCallData) external;

    function cancelMotion(uint256 _motionId) external;

    function getMotions() external view returns (Motion[] memory);

    function addEVMScriptFactory(address _evmScriptFactory, bytes memory _permissions) external;

    function removeEVMScriptFactory(address _evmScriptFactory) external;

    function isEVMScriptFactory(address _maybeEVMScriptFactory) external view returns (bool);

    function setEVMScriptExecutor(address _evmScriptExecutor) external;

    function evmScriptExecutor() external view returns (address);

    function governanceToken() external view returns (address);

    function motionDuration() external view returns (uint256);

    function DEFAULT_ADMIN_ROLE() external view returns (bytes32);

    function hasRole(bytes32 role, address account) external view returns (bool);

    function grantRole(bytes32 role, address account) external;

    function revokeRole(bytes32 role, address account) external;
}

/// @notice The executor's owner, the DAO Voting, may point it at another Easy Track. A test replays
///         a DAO vote by pointing it at the Agent, which then runs a script through it.
interface IEVMScriptExecutor {
    function owner() external view returns (address);

    function callsScript() external view returns (address);

    function easyTrack() external view returns (address);

    function setEasyTrack(address _easyTrack) external;

    function transferOwnership(address newOwner) external;

    function executeEVMScript(bytes memory _evmScript) external returns (bytes memory);
}

/// @notice The registry the reward programs factories add to and remove from.
interface IRewardProgramsRegistry {
    function addRewardProgram(address _rewardProgram, string memory _title) external;

    function removeRewardProgram(address _rewardProgram) external;

    function getRewardPrograms() external view returns (address[] memory);
}
