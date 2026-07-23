// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the Erc4626ExitBook, covering only `setVaultAllowed` — the method
/// `LidoLendActivateMarket` targets. Never called during EVMScript creation; used only so tests can
/// reproduce the exact selector and ABI encoding brownie would produce for the real call.
contract Erc4626ExitBookStub {
    bytes32 public constant ALLOWLIST_MANAGER_ROLE = keccak256("ALLOWLIST_MANAGER_ROLE");

    address public lastVault;
    bool public lastAllowed;
    mapping(address => bool) public isVaultAllowed;
    mapping(bytes32 => mapping(address => bool)) public hasRole;
    bool public enforceRoles;

    function grantRole(bytes32 role, address account) external {
        hasRole[role][account] = true;
    }

    function setEnforceRoles(bool enforce) external {
        enforceRoles = enforce;
    }

    function setVaultAllowed(address vault, bool allowed) external {
        require(
            !enforceRoles || hasRole[ALLOWLIST_MANAGER_ROLE][msg.sender],
            "MISSING_ALLOWLIST_MANAGER_ROLE"
        );
        lastVault = vault;
        lastAllowed = allowed;
        isVaultAllowed[vault] = allowed;
    }
}
