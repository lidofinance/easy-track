from brownie import AdaptiveCurveConfigStub, AdaptiveCurveIrmStub, LidoLendSetMarketIrm
from eth_abi import encode


def test_set_market_irm_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion routes the market to a different IRM curve on the shared IrmRouter."
    irm_router = lido_lend.contract("irmRouter")
    market_id = lido_lend.market["id"]
    market_params = tuple(lido_lend.market[key] for key in ("loanToken", "collateralToken", "oracle", "irm", "lltv"))

    old_irm = irm_router.marketIrm(market_id)  # created_market routed this to the market's curve
    # The production router probes a new IRM before storing it, so configure the target before the routing motion.
    new_irm = AdaptiveCurveIrmStub.deploy({"from": deployer})
    new_config = AdaptiveCurveConfigStub.deploy(lido_lend.market["curveParams"], {"from": deployer})
    new_irm.applyIrmConfig(market_params, new_config, {"from": deployer})
    assert new_irm.address != old_irm

    factory = deployer.deploy(
        LidoLendSetMarketIrm,
        trusted_caller,
        lido_lend.contract("core"),
        irm_router,
    )
    register_factory(factory, permission((irm_router, irm_router.setMarketIrm)))
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32", "address"], [market_id, new_irm.address]).hex(),
        trusted_caller,
    )

    assert new_irm.marketCurveConfig(market_id) == new_config
    assert irm_router.marketIrm(market_id) == new_irm
