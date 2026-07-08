from brownie import LidoLendUnbanGuardianSignals
from eth_abi import encode

BANNED_ACCOUNT = "0x" + "55" * 20


def test_unban_guardian_signals_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion lifts a ban previously latched on the market's GuardianSignals registry."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]

    gs.grantRole(gs.ACCESS_LIMITER_ROLE(), admin, {"from": admin})
    gs.ban(market_id, BANNED_ACCOUNT, {"from": admin})
    assert gs.isBanned(market_id, BANNED_ACCOUNT)

    factory = deployer.deploy(LidoLendUnbanGuardianSignals, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((gs, gs.unban)))
    enact_motion(easy_track, factory, "0x" + encode(["bytes32", "address"], [market_id, BANNED_ACCOUNT]).hex(), trusted_caller)

    assert not gs.isBanned(market_id, BANNED_ACCOUNT)
