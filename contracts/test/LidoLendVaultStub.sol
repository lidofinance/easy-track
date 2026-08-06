// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `LidoLendERC4626`, covering only `marketId()`.
contract LidoLendVaultStub {
    bytes32 public marketId;

    function setMarketId(bytes32 marketId_) external {
        marketId = marketId_;
    }
}
