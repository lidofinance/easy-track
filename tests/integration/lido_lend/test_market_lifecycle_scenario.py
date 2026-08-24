from brownie import LidoLendMarketManagerActions
from eth_abi import encode
from utils.lido_lend import (
    COLLATERAL_ACTIVATION_CONFIG_ABI_TYPE as ACTIVATION_TYPE,
    SETTLEMENT_CONFIG_ABI_TYPE as SETTLEMENT_TYPE,
)

NEW_CAP = 5_000_000 * 10**18

ACTIVATION_CONFIG = (600, 7200, 1000 * 10**18, 10 * 10**18, 3600, 10**16, 10800, 300, 150)

SETTLEMENT_CONFIG = (500, 1000 * 10**18, 5 * 10**18, 100)


def _calldata(action, payload_types, payload_values):
    payload = encode(payload_types, payload_values)
    return "0x" + encode(["uint8", "bytes"], [action, payload]).hex()


def test_market_lifecycle_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "Raise the cap, retune activation + settlement, then freeze (steward) and unfreeze (motion) — all on one live market."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]

    controller.grantRole(controller.FREEZER_ROLE(), admin, {"from": admin})

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendMarketManagerActions, trusted_caller, owner)

    register_factory(
        factory,
        permission(
            (owner, owner.setInstantActivation),
            (owner, owner.setMarketCollateralActivationConfig),
            (owner, owner.setMarketSettlementConfig),
            (owner, owner.setMarketSupplyCap),
            (owner, owner.unfreezeMarket),
        ),
    )

    assert controller.supplyCap() < NEW_CAP
    enact_motion(
        easy_track,
        factory,
        _calldata(3, ["bytes32", "uint256"], [market_id, NEW_CAP]),
        trusted_caller,
    )
    assert controller.supplyCap() == NEW_CAP

    enact_motion(
        easy_track,
        factory,
        _calldata(1, ["bytes32", ACTIVATION_TYPE], [market_id, ACTIVATION_CONFIG]),
        trusted_caller,
    )
    assert controller.collateralActivationConfig() == ACTIVATION_CONFIG

    enact_motion(
        easy_track,
        factory,
        _calldata(2, ["bytes32", SETTLEMENT_TYPE], [market_id, SETTLEMENT_CONFIG]),
        trusted_caller,
    )
    assert controller.settlementConfig() == SETTLEMENT_CONFIG

    controller.freeze({"from": admin})
    assert controller.isFrozen()

    enact_motion(
        easy_track,
        factory,
        _calldata(4, ["bytes32[]"], [[market_id]]),
        trusted_caller,
    )
    assert not controller.isFrozen()
