from brownie import LidoLendSetMarketIrm
from eth_abi import encode


def test_set_market_irm_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion routes the market to an IRM curve on the shared IrmRouter."
    irm_router = lido_lend.contract("irmRouter")
    market_id = lido_lend.market["id"]
    new_irm = lido_lend.market["curve"]

    factory = deployer.deploy(LidoLendSetMarketIrm, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((irm_router, irm_router.setMarketIrm)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "address"], [market_id, new_irm]).hex(), trusted_caller)

    assert irm_router.marketIrm(market_id) == new_irm
