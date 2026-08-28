// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the CircuitBreaker methods targeted by Lido Lend factories.
contract CircuitBreakerStub {
    uint256 public constant MIN_PAUSE_DURATION = 3 days;
    uint256 public constant MAX_PAUSE_DURATION = 30 days;
    uint256 public constant MIN_HEARTBEAT_INTERVAL = 30 days;
    uint256 public constant MAX_HEARTBEAT_INTERVAL = 1095 days;

    address public ADMIN;
    uint256 public pauseDuration = MIN_PAUSE_DURATION;
    uint256 public heartbeatInterval = MIN_HEARTBEAT_INTERVAL;

    address public lastPausable;
    address public lastPauser;
    mapping(address => address) public pausers;

    constructor(address admin) {
        ADMIN = admin;
    }

    function setAdmin(address admin) external {
        ADMIN = admin;
    }

    function registerPauser(address pausable, address newPauser) external {
        require(msg.sender == ADMIN, "NOT_ADMIN");
        lastPausable = pausable;
        lastPauser = newPauser;
        pausers[pausable] = newPauser;
    }

    function setPauseDuration(uint256 newPauseDuration) external {
        require(msg.sender == ADMIN, "NOT_ADMIN");
        require(newPauseDuration >= MIN_PAUSE_DURATION, "PAUSE_DURATION_BELOW_MIN");
        require(newPauseDuration <= MAX_PAUSE_DURATION, "PAUSE_DURATION_ABOVE_MAX");
        pauseDuration = newPauseDuration;
    }

    function setHeartbeatInterval(uint256 newHeartbeatInterval) external {
        require(msg.sender == ADMIN, "NOT_ADMIN");
        require(newHeartbeatInterval >= MIN_HEARTBEAT_INTERVAL, "HEARTBEAT_INTERVAL_BELOW_MIN");
        require(newHeartbeatInterval <= MAX_HEARTBEAT_INTERVAL, "HEARTBEAT_INTERVAL_ABOVE_MAX");
        heartbeatInterval = newHeartbeatInterval;
    }

    function getPauser(address pausable) external view returns (address) {
        return pausers[pausable];
    }
}
