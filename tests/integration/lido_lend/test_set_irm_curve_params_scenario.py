from brownie import interface, LidoLendSetIrmCurveParams, ZERO_ADDRESS
from eth_abi import encode

from utils.lido_lend import CURVE_PARAMS_ABI_TYPE as CURVE_PARAMS_TYPE


def _different_curve_params(current):
    params = list(current)
    params[2] = 850000000000000000 if params[2] != 850000000000000000 else 800000000000000000
    return tuple(params)


def test_set_irm_curve_params_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion reparametrizes the market on the configured AdaptiveCurveIrm singleton."
    market_id = lido_lend.market["id"]
    curve_irm = lido_lend.contract("adaptiveCurveIrm")
    if lido_lend.easy_track:
        config_before = curve_irm.marketCurveConfig(market_id)
        assert config_before != ZERO_ADDRESS
        params_before = tuple(interface.AdaptiveCurveConfig(config_before).getCurveParams())
    else:
        config_before = None
        params_before = tuple(curve_irm.lastCurveParams())
    new_curve_params = _different_curve_params(params_before)
    assert params_before != new_curve_params

    factory = deployer.deploy(
        LidoLendSetIrmCurveParams,
        trusted_caller,
        lido_lend.contract("core"),
        lido_lend.contract("irmRouter"),
        curve_irm,
    )
    register_factory(factory, permission((curve_irm, curve_irm.setMarketCurveParams)))
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32", CURVE_PARAMS_TYPE], [market_id, new_curve_params]).hex(),
        trusted_caller,
    )

    # Post-state: the motion actually wrote the market's curve params on the singleton.
    if lido_lend.easy_track:
        config_after = curve_irm.marketCurveConfig(market_id)
        assert config_after != config_before
        assert tuple(interface.AdaptiveCurveConfig(config_after).getCurveParams()) == new_curve_params
    else:
        assert tuple(curve_irm.lastCurveParams()) == new_curve_params
