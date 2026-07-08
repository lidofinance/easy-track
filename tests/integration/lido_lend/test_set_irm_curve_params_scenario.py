from brownie import LidoLendSetIrmCurveParams
from eth_abi import encode

CURVE_PARAMS_TYPE = "(int256,int256,int256,int256,int256,int256,uint256)"
NEW_CURVE_PARAMS = (4000000000000000000, 1585489599188, 900000000000000000, 634195839, 31709791, 63419583967, 0)


def test_set_irm_curve_params_scenario(
    lido_lend, created_market, route_market_curve, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion reparametrizes the market's Adaptive IRM curve (resolved via the router)."
    market_id = lido_lend.market["id"]
    route_market_curve()
    curve_irm = lido_lend.contract("adaptiveCurveIrm")

    factory = deployer.deploy(LidoLendSetIrmCurveParams, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((curve_irm, curve_irm.setMarketCurveParams)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", CURVE_PARAMS_TYPE], [market_id, NEW_CURVE_PARAMS]).hex(), trusted_caller)
