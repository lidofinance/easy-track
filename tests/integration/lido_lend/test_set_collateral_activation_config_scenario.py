from brownie import LidoLendSetCollateralActivationConfig
from eth_abi import encode

CONFIG_TYPE = "(uint40,uint40,uint128,uint128,uint40,uint128,uint40,uint40,uint40)"
NEW_CONFIG = (600, 7200, 1000 * 10**18, 10 * 10**18, 3600, 10**16, 10800, 300, 150)


def test_set_collateral_activation_config_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion updates the collateral-activation config on the market controller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert controller.collateralActivationConfig() != NEW_CONFIG

    factory = deployer.deploy(LidoLendSetCollateralActivationConfig, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((controller, controller.setCollateralActivationConfig)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", CONFIG_TYPE], [market_id, NEW_CONFIG]).hex(), trusted_caller)

    assert controller.collateralActivationConfig() == NEW_CONFIG
