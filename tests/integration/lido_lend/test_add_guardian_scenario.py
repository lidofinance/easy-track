from brownie import LidoLendAddGuardian
from eth_abi import encode

NEW_GUARDIAN = "0x" + "11" * 20


def test_add_guardian_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion adds a new guardian to the market's GuardianSignals registry."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]
    assert not gs.isGuardian(NEW_GUARDIAN)

    factory = deployer.deploy(LidoLendAddGuardian, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((gs, gs.addGuardian)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "address"], [market_id, NEW_GUARDIAN]).hex(), trusted_caller)

    assert gs.isGuardian(NEW_GUARDIAN)
