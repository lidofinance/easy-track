// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the LidoLend core, covering the market-resolution surface the domain-scoped
/// factories read at motion time: `marketController(id)` and `idToMarketParams(id)`. An unset market
/// resolves to the zero controller / zero-`irm` params, so factories hit their MARKET_NOT_FOUND guard.
contract LidoLendCoreStub {
    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
    }

    mapping(bytes32 => address) public marketController;
    mapping(bytes32 => MarketParams) private _idToMarketParams;

    function setMarketController(bytes32 marketId, address controller) external {
        marketController[marketId] = controller;
    }

    function setMarketParams(bytes32 marketId, MarketParams calldata marketParams) external {
        _idToMarketParams[marketId] = marketParams;
    }

    function idToMarketParams(bytes32 marketId) external view returns (MarketParams memory) {
        return _idToMarketParams[marketId];
    }
}
