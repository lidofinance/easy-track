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
    gs.setQuorum(2, {"from": admin})
    assert gs.isGuardian(GUARDIAN)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendRemoveGuardian, trusted_caller, owner)
    register_factory(
        factory,
        permission((owner, owner.setGuardiansQuorum), (owner, owner.removeGuardian)),
    )
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32", "address", "uint256"], [market_id, GUARDIAN, 1]).hex(),
        trusted_caller,
    )

    assert not gs.isGuardian(GUARDIAN)
    assert gs.getQuorum() == 1
