from brownie import LidoLendRiskStewardActions
from eth_abi import encode

STEWARD = "0x" + "77" * 20
ACTION = 1


def create_calldata(market_id, steward):
    payload = encode(["bytes32", "address"], [market_id, steward])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_remove_risk_steward_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion removes a risk steward for a market on the RiskStewardDashboard."
    dashboard = lido_lend.contract("riskStewardDashboard")
    market_id = lido_lend.market["id"]

    dashboard.grantRole(dashboard.STEWARD_ADMIN_ROLE(), admin, {"from": admin})
    dashboard.addMarketSteward(market_id, STEWARD, {"from": admin})
    assert dashboard.isMarketSteward(market_id, STEWARD)

    factory = deployer.deploy(LidoLendRiskStewardActions, trusted_caller, dashboard)
    register_factory(factory, permission((dashboard, dashboard.removeMarketSteward)))
    enact_motion(easy_track, factory, create_calldata(market_id, STEWARD), trusted_caller)

    assert not dashboard.isMarketSteward(market_id, STEWARD)
