from brownie import LidoLendMarketManagerActions
from eth_abi import encode

from utils.lido_lend import SETTLEMENT_CONFIG_ABI_TYPE as CONFIG_TYPE

NEW_CONFIG = (500, 1000 * 10**18, 5 * 10**18, 100)
ACTION = 2


def create_calldata(market_id, config):
    payload = encode(["bytes32", CONFIG_TYPE], [market_id, config])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_set_settlement_config_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion updates the settlement-slice config on the market controller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert controller.settlementConfig() != NEW_CONFIG

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendMarketManagerActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setMarketSettlementConfig)))
    enact_motion(easy_track, factory, create_calldata(market_id, NEW_CONFIG), trusted_caller)

    assert controller.settlementConfig() == NEW_CONFIG
