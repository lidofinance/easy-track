import pytest
from brownie import LidoLendVaultStub, reverts

INITIAL_FEE = 10**17


@pytest.mark.parametrize("enable_settlement,fee", [(True, INITIAL_FEE), (False, 0)])
def test_activate_market_scenario(
    lido_lend,
    easy_track,
    trusted_caller,
    activate_market,
    enable_settlement,
    fee,
):
    "Activate an inert market with the requested settlement and fee configuration."
    activation = activate_market(enable_settlement, fee)
    core = activation["core"]
    m = lido_lend.market
    market_id = m["id"]
    dashboard = lido_lend.contract("riskStewardDashboard")

    assert core.market(market_id)["lastUpdate"] != 0
    assert core.market(market_id)["fee"] == fee
    assert activation["irm_router"].marketIrm(market_id) == m["curve"]
    assert dashboard.isMarketSteward(market_id, m["steward"])
    assert activation["circuit_breaker"].getPauser(m["controller"]) == m["pauser"]
    assert core.isSettlementEnabled(market_id) == enable_settlement
    if lido_lend.local:
        recipient = activation["preseeder"].PRESEED_RECIPIENT()
        assert core.supplyShares(market_id, recipient) == activation["market_supply_shares"]
        assert LidoLendVaultStub.at(m["vault"]).balanceOf(recipient) >= activation["min_vault_shares"]

    with reverts():
        easy_track.createMotion(activation["factory"], activation["calldata"], {"from": trusted_caller})
