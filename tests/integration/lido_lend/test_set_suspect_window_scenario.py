from brownie import LidoLendGuardianActions
from eth_abi import encode

NEW_WINDOW = 7200
ACTION = 4


def create_calldata(market_id, window):
    payload = encode(["bytes32", "uint256"], [market_id, window])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_set_suspect_window_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory, enact_motion
):
    "A Manager Committee motion sets the suspect window on the market's GuardianSignals registry."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]
    assert gs.getSuspectWindow() != NEW_WINDOW

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.setGuardiansSuspectWindow)))
    enact_motion(easy_track, factory, create_calldata(market_id, NEW_WINDOW), trusted_caller)

    assert gs.getSuspectWindow() == NEW_WINDOW
