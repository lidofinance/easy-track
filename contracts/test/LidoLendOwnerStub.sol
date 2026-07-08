// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `LidoLendOwner` (lido-lend-market/src/periphery/LidoLendOwner.sol),
/// covering only the two-arg `createMarket` overload `LidoLendCreateMarket` calls into.
contract LidoLendOwnerStub {
    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
    }

    MarketParams public lastMarketParams;
    address public lastController;
    bool public lastEnableSettlement;
    bool public called;

    function createMarket(MarketParams calldata marketParams, address controller, bool enableSettlement) external {
        lastMarketParams = marketParams;
        lastController = controller;
        lastEnableSettlement = enableSettlement;
        called = true;
    }
}
