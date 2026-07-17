// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the CircuitBreaker, covering only `registerPauser` — the method
/// `LidoLendActivateMarket` targets. Never called during EVMScript creation; used only so tests can
/// reproduce the exact selector and ABI encoding brownie would produce for the real call.
contract CircuitBreakerStub {
    address public ADMIN;

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

    function getPauser(address pausable) external view returns (address) {
        return pausers[pausable];
    }
}
