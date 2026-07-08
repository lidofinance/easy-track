// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the MorphoExitBook, covering only `setMarketAllowed` — the method
/// `LidoLendActivateMarket` targets. Never called during EVMScript creation; used only so tests can
/// reproduce the exact selector and ABI encoding brownie would produce for the real call.
contract MorphoExitBookStub {
    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
    }

    MarketParams public lastMarketParams;
    bool public lastAllowed;

    function setMarketAllowed(MarketParams calldata marketParams, bool allowed) external {
        lastMarketParams = marketParams;
        lastAllowed = allowed;
    }
}
