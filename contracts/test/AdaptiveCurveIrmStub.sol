// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `AdaptiveCurveIrm` (lido-lend-irm/src/adaptive-curve-irm/AdaptiveCurveIrm.sol),
/// covering only `setMarketCurveParams`.
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

    MarketParams public lastMarketParams;
    AdaptiveCurveParams private _lastCurveParams;

    function setMarketCurveParams(MarketParams memory marketParams, AdaptiveCurveParams calldata curveParams)
        external
    {
        lastMarketParams = marketParams;
        _lastCurveParams = curveParams;
    }

    function lastCurveParams() external view returns (AdaptiveCurveParams memory) {
        return _lastCurveParams;
    }
}
