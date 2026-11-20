import pytest
from brownie import interface, LidoLendMarketManagerActions, LidoLendMarketControllerStub
from eth_abi import encode

ACTION = 4


def create_calldata(market_ids):
    payload = encode(["bytes32[]"], [market_ids])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_unfreeze_market_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion unfreezes a market that a risk steward previously froze."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]

    controller.grantRole(controller.FREEZER_ROLE(), admin, {"from": admin})
    controller.freeze({"from": admin})
    assert controller.isFrozen()

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendMarketManagerActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.unfreezeMarket)))
    enact_motion(easy_track, factory, create_calldata([market_id]), trusted_caller)

    assert not controller.isFrozen()


def test_unfreeze_mixed_markets_scenario(
    lido_lend, created_markets, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A single motion unfreezes a frozen market and succeeds for an already unfrozen market."
    owner = lido_lend.contract("owner")
    if lido_lend.local:
        frozen_controller = lido_lend.contract("controller")
        frozen_market_id = lido_lend.market["id"]
        unfrozen_controller = LidoLendMarketControllerStub.deploy({"from": deployer})
        unfrozen_market_id = (2).to_bytes(32, "big")
        lido_lend.contract("core").setMarketController(unfrozen_market_id, unfrozen_controller, {"from": deployer})
        unfrozen_controller.grantRole(unfrozen_controller.UNFREEZER_ROLE(), owner, {"from": deployer})
        unfrozen_controller.setEnforceRoles(True, {"from": deployer})
    else:
        if len(lido_lend.markets) < 2:
            raise pytest.UsageError("artifact mode requires at least two markets for the cross-market scenario")
        frozen_market, unfrozen_market = lido_lend.markets[:2]
        frozen_market_id, unfrozen_market_id = frozen_market["id"], unfrozen_market["id"]
        frozen_controller = interface.LidoLendMarketController(frozen_market["controller"])
        unfrozen_controller = interface.LidoLendMarketController(unfrozen_market["controller"])

    frozen_controller.grantRole(frozen_controller.FREEZER_ROLE(), admin, {"from": admin})
    frozen_controller.freeze({"from": admin})
    unfrozen_controller.grantRole(unfrozen_controller.UNFREEZER_ROLE(), admin, {"from": admin})
    unfrozen_controller.unfreeze({"from": admin})
    assert frozen_controller.isFrozen()
    assert not unfrozen_controller.isFrozen()

    factory = deployer.deploy(LidoLendMarketManagerActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.unfreezeMarket)))
    enact_motion(easy_track, factory, create_calldata([frozen_market_id, unfrozen_market_id]), trusted_caller)

    assert not frozen_controller.isFrozen()
    assert not unfrozen_controller.isFrozen()
