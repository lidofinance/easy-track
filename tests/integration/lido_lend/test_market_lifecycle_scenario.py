
from brownie import (
    LidoLendSetSupplyCap,
    LidoLendSetCollateralActivationConfig,
    LidoLendSetSettlementConfig,
    LidoLendUnfreezeMarket,
)
from eth_abi import encode

NEW_CAP = 5_000_000 * 10**18

ACTIVATION_TYPE = "(uint40,uint40,uint128,uint128,uint40,uint128,uint40,uint40,uint40)"
ACTIVATION_CONFIG = (600, 7200, 1000 * 10**18, 10 * 10**18, 3600, 10**16, 10800, 300, 150)

SETTLEMENT_TYPE = "(uint16,uint96,uint96,uint16)"
SETTLEMENT_CONFIG = (500, 1000 * 10**18, 5 * 10**18, 100)


def test_market_lifecycle_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "Raise the cap, retune activation + settlement, then freeze (steward) and unfreeze (motion) — all on one live market."
    controller = lido_lend.contract("controller")
    core = lido_lend.contract("core")
    market_id = lido_lend.market["id"]

    controller.grantRole(controller.FREEZER_ROLE(), admin, {"from": admin})

    cap_factory = deployer.deploy(LidoLendSetSupplyCap, trusted_caller, core)
    activation_factory = deployer.deploy(LidoLendSetCollateralActivationConfig, trusted_caller, core)
    settlement_factory = deployer.deploy(LidoLendSetSettlementConfig, trusted_caller, core)
    unfreeze_factory = deployer.deploy(LidoLendUnfreezeMarket, trusted_caller, core)

    register_factory(cap_factory, permission((controller, controller.setSupplyCap)))
    register_factory(activation_factory, permission((controller, controller.setCollateralActivationConfig)))
    register_factory(settlement_factory, permission((controller, controller.setSettlementConfig)))
    register_factory(unfreeze_factory, permission((controller, controller.unfreeze)))

    assert controller.supplyCap() < NEW_CAP
    enact_motion(easy_track, cap_factory, "0x" + encode(["bytes32", "uint256"], [market_id, NEW_CAP]).hex(), trusted_caller)
    assert controller.supplyCap() == NEW_CAP

    enact_motion(
        easy_track, activation_factory,
        "0x" + encode(["bytes32", ACTIVATION_TYPE], [market_id, ACTIVATION_CONFIG]).hex(), trusted_caller,
    )
    assert controller.collateralActivationConfig() == ACTIVATION_CONFIG

    enact_motion(
        easy_track, settlement_factory,
        "0x" + encode(["bytes32", SETTLEMENT_TYPE], [market_id, SETTLEMENT_CONFIG]).hex(), trusted_caller,
    )
    assert controller.settlementConfig() == SETTLEMENT_CONFIG

    controller.freeze({"from": admin})
    assert controller.isFrozen()

    enact_motion(easy_track, unfreeze_factory, "0x" + encode(["bytes32"], [market_id]).hex(), trusted_caller)
    assert not controller.isFrozen()
