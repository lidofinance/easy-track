"""Shared constants for the Lido Lend EasyTrack factory tests.

Single source of truth for the ABI tuple types the factories encode/decode. These layouts are
independently cross-checked against the deployed ABIs by
`tests/evm_script_factories/test_lido_lend_interface_sync.py` (which intentionally does NOT import from
here — it is the independent oracle).
"""

# MarketParams: (loanToken, collateralToken, oracle, irm, lltv)
MARKET_PARAMS_ABI_TYPE = "(address,address,address,address,uint256)"

# AdaptiveCurveParams: (curveSteepness, adjustmentSpeed, targetUtilization, initialRateAtTarget,
#                       minRateAtTarget, maxRateAtTarget, maxBorrowRate)
CURVE_PARAMS_ABI_TYPE = "(int256,int256,int256,int256,int256,int256,uint256)"

# ILidoLendMarketController.CollateralActivationConfig
COLLATERAL_ACTIVATION_CONFIG_ABI_TYPE = "(uint40,uint40,uint128,uint128,uint40,uint128,uint40,uint40,uint40)"

# ILidoLendMarketController.SettlementConfig
SETTLEMENT_CONFIG_ABI_TYPE = "(uint16,uint96,uint96,uint16)"
