from brownie import LidoLendSetMarketIrm, AdaptiveCurveIrmStub
from eth_abi import encode


def test_set_market_irm_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion routes the market to a different IRM curve on the shared IrmRouter."
    irm_router = lido_lend.contract("irmRouter")
    market_id = lido_lend.market["id"]

    old_irm = irm_router.marketIrm(market_id)  # created_market routed this to the market's curve
    if lido_lend.easy_track:
        new_irm = lido_lend.market["curve"]  # real deployment: (re)route to the domain curve
    else:
        # Local mock: a distinct curve so the motion causes an observable re-route, not a no-op.
        new_irm = AdaptiveCurveIrmStub.deploy({"from": deployer}).address
        assert new_irm != old_irm

    factory = deployer.deploy(
        LidoLendSetMarketIrm,
        trusted_caller,
        lido_lend.contract("core"),
        irm_router,
    )
    register_factory(factory, permission((irm_router, irm_router.setMarketIrm)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "address"], [market_id, new_irm]).hex(), trusted_caller)

    assert irm_router.marketIrm(market_id) == new_irm
