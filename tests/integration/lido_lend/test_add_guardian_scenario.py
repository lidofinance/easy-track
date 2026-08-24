from brownie import LidoLendGuardianActions
from eth_abi import encode

NEW_GUARDIAN = "0x" + "11" * 20
ACTION = 0


def create_calldata(market_id, guardian, new_quorum):
    payload = encode(["bytes32", "address", "uint256"], [market_id, guardian, new_quorum])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_add_guardian_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion adds a new guardian to the market's GuardianSignals registry."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]
    assert not gs.isGuardian(NEW_GUARDIAN)
    old_quorum = gs.getQuorum()

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, owner)
    register_factory(
        factory,
        permission((owner, owner.addGuardian), (owner, owner.setGuardiansQuorum)),
    )
    enact_motion(
        easy_track,
        factory,
        create_calldata(market_id, NEW_GUARDIAN, old_quorum + 1),
        trusted_caller,
    )

    assert gs.isGuardian(NEW_GUARDIAN)
    assert gs.getQuorum() == old_quorum + 1
