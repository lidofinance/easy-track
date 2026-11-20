from brownie import LidoLendMarketManagerActions
from eth_abi import encode

from utils.lido_lend import COLLATERAL_ACTIVATION_CONFIG_ABI_TYPE as CONFIG_TYPE

NEW_CONFIG = (600, 7200, 1000 * 10**18, 10**15, 3600, 10**16, 10800, 300, 150)
ACTION = 1


def create_calldata(market_id, config):
    payload = encode(["bytes32", CONFIG_TYPE], [market_id, config])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_set_collateral_activation_config_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion updates the collateral-activation config on the market controller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert controller.collateralActivationConfig() != NEW_CONFIG

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendMarketManagerActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setMarketCollateralActivationConfig)))
    enact_motion(easy_track, factory, create_calldata(market_id, NEW_CONFIG), trusted_caller)

    assert controller.collateralActivationConfig() == NEW_CONFIG
