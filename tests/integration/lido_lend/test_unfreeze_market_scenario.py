from brownie import LidoLendUnfreezeMarket
from eth_abi import encode


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
    factory = deployer.deploy(LidoLendUnfreezeMarket, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.unfreezeMarket)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32[]"], [[market_id]]).hex(), trusted_caller)

    assert not controller.isFrozen()
