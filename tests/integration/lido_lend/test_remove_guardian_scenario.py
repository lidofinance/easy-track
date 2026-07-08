from brownie import LidoLendRemoveGuardian
from eth_abi import encode

GUARDIAN = "0x" + "22" * 20


def test_remove_guardian_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion removes an existing guardian from the market's GuardianSignals registry."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]

    gs.grantRole(gs.MANAGER_ROLE(), admin, {"from": admin})
    gs.addGuardian(GUARDIAN, {"from": admin})
    assert gs.isGuardian(GUARDIAN)

    factory = deployer.deploy(LidoLendRemoveGuardian, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((gs, gs.removeGuardian)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "address"], [market_id, GUARDIAN]).hex(), trusted_caller)

    assert not gs.isGuardian(GUARDIAN)
