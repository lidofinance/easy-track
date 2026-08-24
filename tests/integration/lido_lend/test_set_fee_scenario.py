from brownie import LidoLendSetFee
from eth_abi import encode


def test_set_fee_scenario(
    lido_lend,
    created_market,
    easy_track,
    deployer,
    trusted_caller,
    permission,
    register_factory,
    enact_motion,
):
    "A fee motion changes one market fee through the facade; the target accrues before writing it."
    core = lido_lend.contract("core")
    owner = lido_lend.contract("owner")
    market = lido_lend.market
    current_fee = core.market(market["id"])[5]
    new_fee = 10**17 if current_fee != 10**17 else 5 * 10**16

    factory = deployer.deploy(LidoLendSetFee, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setFee)))
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32", "uint256"], [market["id"], new_fee]).hex(),
        trusted_caller,
    )

    assert core.market(market["id"])[5] == new_fee
