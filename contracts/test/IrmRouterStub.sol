// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

struct RouterStubMarketParams {
    address loanToken;
    address collateralToken;
    address oracle;
    address irm;
    uint256 lltv;
}

interface IAdaptiveCurveProbe {
    function borrowRate(RouterStubMarketParams calldata marketParams)
        external
        view
        returns (uint256);
}

/// @author (draft)
/// @notice Test-only stub of the IrmRouter. `setMarketIrm` is manager-gated (so an executor lacking the
/// manager role is caught), and `borrowRate` reverts while a market is unrouted, otherwise delegating to the
/// routed curve — together this reproduces the revert `createMarket` hits when activation is mis-ordered.
contract IrmRouterStub {
    RouterStubMarketParams public lastMarketParams;
    address public lastIrm;
    address public manager;
    address public MORPHO;

    /// @notice Per-market curve the router routes to (read by LidoLendApplyIrmConfig).
    mapping(bytes32 => address) public marketIrm;

    constructor() {
        manager = msg.sender;
    }

    function setManager(address manager_) external {
        manager = manager_;
    }

    function setMorpho(address morpho_) external {
        MORPHO = morpho_;
    }

    /// @notice Test-only helper to seed routing without the manager gate (used to set up unit-test state).
    function setMarketCurve(bytes32 marketId, address curve) external {
        marketIrm[marketId] = curve;
    }

    function setMarketIrm(RouterStubMarketParams calldata marketParams, address irm) external {
        require(msg.sender == manager, "NOT_MANAGER");
        lastMarketParams = marketParams;
        lastIrm = irm;
        marketIrm[keccak256(abi.encode(marketParams))] = irm;
    }

    /// @notice Mirrors the router: reverts if the market is unrouted, else delegates to the routed curve
    /// (whose own ping reverts if its params are unset). `createMarket` calls this on the market's `irm`.
    function borrowRate(RouterStubMarketParams calldata marketParams)
        external
        view
        returns (uint256)
    {
        address irm = marketIrm[keccak256(abi.encode(marketParams))];
        require(irm != address(0), "MARKET_NOT_ROUTED");
        return IAdaptiveCurveProbe(irm).borrowRate(marketParams);
    }
}
