// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the Erc4626ExitBook, covering only `setVaultAllowed` — the method
/// `LidoLendActivateMarket` targets. Never called during EVMScript creation; used only so tests can
/// reproduce the exact selector and ABI encoding brownie would produce for the real call.
contract Erc4626ExitBookStub {
    address public lastVault;
    bool public lastAllowed;

    function setVaultAllowed(address vault, bool allowed) external {
        lastVault = vault;
        lastAllowed = allowed;
    }
}
