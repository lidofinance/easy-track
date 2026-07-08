from brownie import LidoLendSetSupplyCap
from eth_abi import encode

NEW_CAP = 5_000_000 * 10**18


def test_set_supply_cap_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion raises the market supply cap on its controller."
    controller = lido_lend.contract("controller")
    market_id = lido_lend.market["id"]
    assert controller.supplyCap() < NEW_CAP

    factory = deployer.deploy(LidoLendSetSupplyCap, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((controller, controller.setSupplyCap)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "uint256"], [market_id, NEW_CAP]).hex(), trusted_caller)

    assert controller.supplyCap() == NEW_CAP
