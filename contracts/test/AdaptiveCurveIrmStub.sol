// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `AdaptiveCurveIrm` (lido-lend-irm/src/adaptive-curve-irm/AdaptiveCurveIrm.sol).
/// Models two behaviours the activation flow depends on: `applyIrmConfig` is manager-gated (so an
/// executor lacking the manager role is caught), and the `borrowRate` ping reverts until a market's curve
/// config is applied — which is what makes `createMarket` revert when activation is mis-ordered.
contract AdaptiveCurveIrmStub {
    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
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
    address public lastConfig;
    address public manager;
    address public ROUTER;
    mapping(bytes32 => address) public marketCurveConfig;
    /// @notice Per-market flag: was a config ever applied to this market? Gates `borrowRate`.
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

    function applyIrmConfig(MarketParams calldata marketParams, address config) external {
        require(msg.sender == manager, "NOT_MANAGER");
        lastMarketParams = marketParams;
        lastConfig = config;
        bytes32 marketId = keccak256(abi.encode(marketParams));
        marketCurveConfig[marketId] = config;
        isCurveConfigured[marketId] = true;
    }

    /// @notice Mirrors the real IRM: the first `borrowRate` ping reverts while the market's config is
    /// unset. `createMarket` performs this ping, so activation must apply the config first.
    function borrowRate(MarketParams calldata marketParams) external view returns (uint256) {
        require(isCurveConfigured[keccak256(abi.encode(marketParams))], "CURVE_NOT_CONFIGURED");
        return 0;
    }

    /// @notice Production IrmRouter probes this Morpho-compatible overload when re-routing a live market.
    function borrowRate(MarketParams calldata marketParams, Market calldata)
        external
        view
        returns (uint256)
    {
        require(isCurveConfigured[keccak256(abi.encode(marketParams))], "CURVE_NOT_CONFIGURED");
        return 0;
    }
}
