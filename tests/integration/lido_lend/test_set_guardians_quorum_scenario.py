from brownie import LidoLendSetGuardiansQuorum
from eth_abi import encode

NEW_QUORUM = 2
EXTRA_GUARDIAN = "0x" + "c3" * 20


def test_set_guardians_quorum_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion changes the guardian quorum on the market's GuardianSignals registry."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]

    gs.grantRole(gs.MANAGER_ROLE(), admin, {"from": admin})
    if not gs.isGuardian(EXTRA_GUARDIAN):
        gs.addGuardian(EXTRA_GUARDIAN, {"from": admin})
    assert gs.getGuardianCount() >= NEW_QUORUM
    assert gs.getQuorum() != NEW_QUORUM

    factory = deployer.deploy(LidoLendSetGuardiansQuorum, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((gs, gs.setQuorum)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "uint256"], [market_id, NEW_QUORUM]).hex(), trusted_caller)

    assert gs.getQuorum() == NEW_QUORUM
