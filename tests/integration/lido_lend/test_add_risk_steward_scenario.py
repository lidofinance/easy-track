from brownie import LidoLendRiskStewardActions
from eth_abi import encode

STEWARD = "0x" + "66" * 20
ACTION = 0


def create_calldata(market_id, steward):
    payload = encode(["bytes32", "address"], [market_id, steward])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_add_risk_steward_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion appoints a risk steward for a market on the RiskStewardDashboard."
    dashboard = lido_lend.contract("riskStewardDashboard")
    market_id = lido_lend.market["id"]
    assert not dashboard.isMarketSteward(market_id, STEWARD)

    factory = deployer.deploy(LidoLendRiskStewardActions, trusted_caller, dashboard)
    register_factory(factory, permission((dashboard, dashboard.addMarketSteward)))
    enact_motion(easy_track, factory, create_calldata(market_id, STEWARD), trusted_caller)

    assert dashboard.isMarketSteward(market_id, STEWARD)
