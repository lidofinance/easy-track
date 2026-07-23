from brownie import LidoLendReplaceGuardian
from eth_abi import encode

OLD_GUARDIAN = "0x" + "33" * 20
NEW_GUARDIAN = "0x" + "44" * 20


def test_replace_guardian_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion swaps one guardian for another (remove old + add new) in one script."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]

    gs.grantRole(gs.MANAGER_ROLE(), admin, {"from": admin})
    gs.addGuardian(OLD_GUARDIAN, {"from": admin})
    assert gs.isGuardian(OLD_GUARDIAN)
    assert not gs.isGuardian(NEW_GUARDIAN)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendReplaceGuardian, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.removeGuardian), (owner, owner.addGuardian)))
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32", "address", "address"], [market_id, OLD_GUARDIAN, NEW_GUARDIAN]).hex(),
        trusted_caller,
    )

    assert not gs.isGuardian(OLD_GUARDIAN)
    assert gs.isGuardian(NEW_GUARDIAN)
