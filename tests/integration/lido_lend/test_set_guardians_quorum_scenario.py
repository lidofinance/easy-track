from brownie import LidoLendGuardianActions
from eth_abi import encode

NEW_QUORUM = 2
EXTRA_GUARDIAN = "0x" + "c3" * 20
ACTION = 3


def create_calldata(market_id, quorum):
    payload = encode(["bytes32", "uint256"], [market_id, quorum])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


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

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setGuardiansQuorum)))
    enact_motion(easy_track, factory, create_calldata(market_id, NEW_QUORUM), trusted_caller)

    assert gs.getQuorum() == NEW_QUORUM
