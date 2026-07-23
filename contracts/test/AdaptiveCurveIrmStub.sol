// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `AdaptiveCurveIrm` (lido-lend-irm/src/adaptive-curve-irm/AdaptiveCurveIrm.sol).
/// Models two behaviours the activation flow depends on: `setMarketCurveParams` is manager-gated (so an
/// executor lacking the manager role is caught), and the `borrowRate` ping reverts until a market's curve
/// params are set — which is what makes `createMarket` revert when activation is mis-ordered.
contract AdaptiveCurveIrmStub {
    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
    }

    struct AdaptiveCurveParams {
        int256 curveSteepness;
        int256 adjustmentSpeed;
        int256 targetUtilization;
        int256 initialRateAtTarget;
        int256 minRateAtTarget;
        int256 maxRateAtTarget;
        uint256 maxBorrowRate;
    }

    struct Market {
        uint128 totalSupplyAssets;
        uint128 totalSupplyShares;
        uint128 totalBorrowAssets;
        uint128 totalBorrowShares;
        uint128 lastUpdate;
        uint128 fee;
    }

    MarketParams public lastMarketParams;
    AdaptiveCurveParams private _lastCurveParams;
    address public manager;
    address public ROUTER;
    /// @notice Per-market flag: were this market's curve params ever set? Gates `borrowRate`.
    mapping(bytes32 => bool) public isCurveConfigured;

    constructor() {
        manager = msg.sender;
    }

    function setManager(address manager_) external {
        manager = manager_;
    }

    function setRouter(address router_) external {
        ROUTER = router_;
    }

    function setMarketCurveParams(MarketParams memory marketParams, AdaptiveCurveParams calldata curveParams) external {
        require(msg.sender == manager, "NOT_MANAGER");
        lastMarketParams = marketParams;
        _lastCurveParams = curveParams;
        isCurveConfigured[keccak256(abi.encode(marketParams))] = true;
    }

    function lastCurveParams() external view returns (AdaptiveCurveParams memory) {
        return _lastCurveParams;
    }

    /// @notice Mirrors the real IRM: the first `borrowRate` ping reverts while the market's curve params are
    /// unset. `createMarket` performs this ping, so activation must set the curve params first.
    function borrowRate(MarketParams calldata marketParams) external view returns (uint256) {
        require(isCurveConfigured[keccak256(abi.encode(marketParams))], "CURVE_NOT_CONFIGURED");
        return 0;
    }

    /// @notice Production IrmRouter probes this Morpho-compatible overload when re-routing a live market.
    function borrowRate(MarketParams calldata, Market calldata) external pure returns (uint256) {
        return 0;
    }
}
