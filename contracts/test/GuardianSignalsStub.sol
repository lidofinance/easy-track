// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `GuardianSignals` (lido-lend-market/src/GuardianSignals.sol),
/// covering the surface the guardian factories call into (`unban` / `isBanned`, the guardian set,
/// and the quorum).
contract GuardianSignalsStub {
    mapping(bytes32 => mapping(address => bool)) public isBanned;
    mapping(address => bool) public isGuardian;
    uint256 private _quorum;
    uint256 private _guardianCount;
    uint256 private _suspectWindow;
    bytes32 public lastUnbannedMarketId;
    address public lastUnbannedAccount;

    function setBanned(bytes32 marketId, address account, bool banned) external {
        isBanned[marketId][account] = banned;
    }

    function setGuardian(address guardian, bool value) external {
        _setGuardian(guardian, value);
    }

    function unban(bytes32 marketId, address account) external {
        isBanned[marketId][account] = false;
        lastUnbannedMarketId = marketId;
        lastUnbannedAccount = account;
    }

    function addGuardian(address guardian) external {
        _setGuardian(guardian, true);
    }

    function removeGuardian(address guardian) external {
        _setGuardian(guardian, false);
    }

    function _setGuardian(address guardian, bool value) internal {
        if (isGuardian[guardian] == value) return;
        isGuardian[guardian] = value;
        _guardianCount = value ? _guardianCount + 1 : _guardianCount - 1;
    }

    function getGuardianCount() external view returns (uint256) {
        return _guardianCount;
    }

    function setQuorum(uint256 newQuorum) external {
        _quorum = newQuorum;
    }

    function getQuorum() external view returns (uint256) {
        return _quorum;
    }

    function setSuspectWindow(uint256 suspectWindow) external {
        _suspectWindow = suspectWindow;
    }

    function getSuspectWindow() external view returns (uint256) {
        return _suspectWindow;
    }
}
