// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `GuardianSignals` (lido-lend-market/src/GuardianSignals.sol),
/// covering the surface the guardian factories call into (`unban` / `isBanned`, the guardian set,
/// and the quorum).
contract GuardianSignalsStub {
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");
    bytes32 public constant ACCESS_RESTORER_ROLE = keccak256("ACCESS_RESTORER_ROLE");
    bytes32 public constant ACCESS_LIMITER_ROLE = keccak256("ACCESS_LIMITER_ROLE");

    mapping(bytes32 => mapping(address => bool)) public isBanned;
    mapping(address => bool) public isGuardian;
    mapping(bytes32 => mapping(address => bool)) public hasRole;
    bool public enforceRoles;
    uint256 private _quorum;
    uint256 private _guardianCount;
    uint256 private _suspectWindow;
    bytes32 public lastUnbannedMarketId;
    address public lastUnbannedAccount;

    modifier onlyRoleWhenEnforced(bytes32 role) {
        require(!enforceRoles || hasRole[role][msg.sender], "GUARDIANS_MISSING_ROLE");
        _;
    }

    function grantRole(bytes32 role, address account) external {
        hasRole[role][account] = true;
    }

    function setEnforceRoles(bool value) external {
        enforceRoles = value;
    }

    function setBanned(
        bytes32 marketId,
        address account,
        bool banned
    ) external {
        isBanned[marketId][account] = banned;
    }

    function ban(bytes32 marketId, address account)
        external
        onlyRoleWhenEnforced(ACCESS_LIMITER_ROLE)
    {
        isBanned[marketId][account] = true;
    }

    function setGuardian(address guardian, bool value) external {
        _setGuardian(guardian, value);
    }

    function unban(bytes32 marketId, address account)
        external
        onlyRoleWhenEnforced(ACCESS_RESTORER_ROLE)
    {
        isBanned[marketId][account] = false;
        lastUnbannedMarketId = marketId;
        lastUnbannedAccount = account;
    }

    function addGuardian(address guardian) external onlyRoleWhenEnforced(MANAGER_ROLE) {
        _setGuardian(guardian, true);
    }

    function removeGuardian(address guardian) external onlyRoleWhenEnforced(MANAGER_ROLE) {
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

    function setQuorum(uint256 newQuorum) external onlyRoleWhenEnforced(MANAGER_ROLE) {
        _quorum = newQuorum;
    }

    function getQuorum() external view returns (uint256) {
        return _quorum;
    }

    function setSuspectWindow(uint256 suspectWindow) external onlyRoleWhenEnforced(MANAGER_ROLE) {
        _suspectWindow = suspectWindow;
    }

    function getSuspectWindow() external view returns (uint256) {
        return _suspectWindow;
    }
}
