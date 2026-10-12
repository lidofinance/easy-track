from brownie import AdaptiveCurveConfigStub, LidoLendApplyIrmConfig, interface
from eth_abi import encode


def _different_curve_params(current):
    params = list(current)
    params[2] = 850000000000000000 if params[2] != 850000000000000000 else 800000000000000000
    return tuple(params)


def test_apply_irm_config_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion applies a new external config to the market's AdaptiveCurveIrm."
    market_id = lido_lend.market["id"]
    adaptive_curve_irm = lido_lend.contract("adaptiveCurveIrm")
    config_before = adaptive_curve_irm.marketCurveConfig(market_id)
    core = lido_lend.contract("core")
    params_before = tuple(interface.AdaptiveCurveConfig(config_before).getCurveParams())
    new_curve_params = _different_curve_params(params_before)
    new_config = deployer.deploy(AdaptiveCurveConfigStub, new_curve_params)

    factory = deployer.deploy(
        LidoLendApplyIrmConfig,
        trusted_caller,
        core,
        lido_lend.contract("irmRouter"),
        adaptive_curve_irm,
    )
    register_factory(
        factory,
        permission((core, core.accrueInterest), (adaptive_curve_irm, adaptive_curve_irm.applyIrmConfig)),
    )
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32", "address"], [market_id, new_config.address]).hex(),
        trusted_caller,
    )

    config_after = adaptive_curve_irm.marketCurveConfig(market_id)
    assert config_after == new_config
    assert config_after != config_before
    assert tuple(interface.AdaptiveCurveConfig(config_after).getCurveParams()) == new_curve_params
