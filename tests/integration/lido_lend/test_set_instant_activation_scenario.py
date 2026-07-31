from brownie import LidoLendSetInstantActivation
from eth_abi import encode

CALLER = "0x" + "d1" * 20


def test_set_instant_activation_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "Manager Committee motions enable and disable instant collateral activation for a caller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert not controller.hasInstantActivation(CALLER)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendSetInstantActivation, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setInstantActivation)))
    calldata_types = ["bytes32", "address", "bool"]
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(calldata_types, [market_id, CALLER, True]).hex(),
        trusted_caller,
    )

    assert controller.hasInstantActivation(CALLER)

    enact_motion(
        easy_track,
        factory,
        "0x" + encode(calldata_types, [market_id, CALLER, False]).hex(),
        trusted_caller,
    )
    assert not controller.hasInstantActivation(CALLER)
