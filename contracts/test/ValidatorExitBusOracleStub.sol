// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

contract ValidatorExitBusOracleStub {
    // This is a stub contract for testing purposes.
    // It simulates the behavior of the Validators Exit Bus Oracle for testing purposes.

    event ExitRequestsSubmitted(bytes32 exitRequestsHash);

    /// @notice Simulates submitting exit requests hash to the Validators Exit Bus Oracle.
    /// @param exitRequestsHash The hash of the exit requests to be submitted.
    /// @dev Emits an event to simulate the submission.
    function submitExitRequestsHash(bytes32 exitRequestsHash) external {
        emit ExitRequestsSubmitted(exitRequestsHash);
    }
}
