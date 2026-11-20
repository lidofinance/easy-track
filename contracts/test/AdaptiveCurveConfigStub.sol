// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Test-only immutable-like config implementing AdaptiveCurveIrm's expected getter.
contract AdaptiveCurveConfigStub {
    struct AdaptiveCurveParams {
        int256 curveSteepness;
        int256 adjustmentSpeed;
        int256 targetUtilization;
        int256 initialRateAtTarget;
        int256 minRateAtTarget;
        int256 maxRateAtTarget;
        uint256 maxBorrowRate;
    }

    AdaptiveCurveParams private _curveParams;

    constructor(AdaptiveCurveParams memory curveParams) {
        _curveParams = curveParams;
    }

    function getCurveParams() external view returns (AdaptiveCurveParams memory) {
        return _curveParams;
    }
}
