from brownie import LidoLendAddRiskSteward
from eth_abi import encode

STEWARD = "0x" + "66" * 20


def test_add_risk_steward_scenario(lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion):
    "A Manager Committee motion appoints a risk steward for a market on the RiskStewardDashboard."
    dashboard = lido_lend.contract("riskStewardDashboard")
    market_id = lido_lend.market["id"]
    assert not dashboard.isMarketSteward(market_id, STEWARD)

    factory = deployer.deploy(LidoLendAddRiskSteward, trusted_caller, lido_lend.contract("core"), dashboard)
    register_factory(factory, permission((dashboard, dashboard.addMarketSteward)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "address"], [market_id, STEWARD]).hex(), trusted_caller)

    assert dashboard.isMarketSteward(market_id, STEWARD)
