from brownie import LidoLendGrantInstantActivation
from eth_abi import encode

CALLER = "0x" + "d1" * 20


def test_grant_instant_activation_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion grants instant collateral activation to a caller on the market controller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert not controller.hasInstantActivation(CALLER)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendGrantInstantActivation, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.grantMarketInstantActivation)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "address"], [market_id, CALLER]).hex(), trusted_caller)

    assert controller.hasInstantActivation(CALLER)
