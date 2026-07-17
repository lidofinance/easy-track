from brownie import LidoLendSetSettlementConfig
from eth_abi import encode

from utils.lido_lend import SETTLEMENT_CONFIG_ABI_TYPE as CONFIG_TYPE
NEW_CONFIG = (500, 1000 * 10**18, 5 * 10**18, 100)


def test_set_settlement_config_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion updates the settlement-slice config on the market controller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert controller.settlementConfig() != NEW_CONFIG

    factory = deployer.deploy(LidoLendSetSettlementConfig, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((controller, controller.setSettlementConfig)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", CONFIG_TYPE], [market_id, NEW_CONFIG]).hex(), trusted_caller)

    assert controller.settlementConfig() == NEW_CONFIG
