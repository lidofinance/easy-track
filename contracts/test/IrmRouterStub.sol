// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the IrmRouter, covering only `setMarketIrm` — the method
/// `LidoLendActivateMarket` targets. Never called during EVMScript creation; used only so tests can
/// reproduce the exact selector and ABI encoding brownie would produce for the real call.
contract IrmRouterStub {
    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
    }

    MarketParams public lastMarketParams;
    address public lastIrm;

    /// @notice Per-market curve config the router routes to (read by LidoLendSetIrmCurveParams).
    mapping(bytes32 => address) public marketIrm;

    function setMarketCurve(bytes32 marketId, address curve) external {
        marketIrm[marketId] = curve;
    }

    function setMarketIrm(MarketParams calldata marketParams, address irm) external {
        lastMarketParams = marketParams;
        lastIrm = irm;
    }
}
