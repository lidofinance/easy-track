from brownie import LidoLendSetSupplyCap
from eth_abi import encode

NEW_CAP = 5_000_000 * 10**18
INITIAL_CAP = NEW_CAP * 2


def test_set_supply_cap_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion can lower the market supply cap via the LidoLendOwner facade."
    controller = lido_lend.contract("controller")
    owner = lido_lend.contract("owner")
    market_id = lido_lend.market["id"]
    controller.grantRole(controller.MANAGER_ROLE(), admin, {"from": admin})
    controller.setSupplyCap(INITIAL_CAP, {"from": admin})
    assert controller.supplyCap() > NEW_CAP

    factory = deployer.deploy(LidoLendSetSupplyCap, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setMarketSupplyCap)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "uint256"], [market_id, NEW_CAP]).hex(), trusted_caller)

    assert controller.supplyCap() == NEW_CAP
