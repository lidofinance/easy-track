from brownie import LidoLendMarketManagerActions
from eth_abi import encode

CALLER = "0x" + "d1" * 20
ACTION = 0


def create_calldata(market_id, caller, enabled):
    payload = encode(["bytes32", "address", "bool"], [market_id, caller, enabled])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_set_instant_activation_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "Manager Committee motions enable and disable instant collateral activation for a caller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert not controller.hasInstantActivation(CALLER)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendMarketManagerActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setInstantActivation)))
    enact_motion(
        easy_track,
        factory,
        create_calldata(market_id, CALLER, True),
        trusted_caller,
    )

    assert controller.hasInstantActivation(CALLER)

    enact_motion(
        easy_track,
        factory,
        create_calldata(market_id, CALLER, False),
        trusted_caller,
    )
    assert not controller.hasInstantActivation(CALLER)
