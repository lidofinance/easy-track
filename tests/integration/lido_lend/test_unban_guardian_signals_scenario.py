import pytest
from brownie import LidoLendUnbanGuardianSignals, LidoLendMarketControllerStub, GuardianSignalsStub
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
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32[]", "address"], [[market_id], BANNED_ACCOUNT]).hex(),
        trusted_caller,
    )

    assert not gs.isBanned(market_id, BANNED_ACCOUNT)


def test_unban_guardian_signals_multi_market_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A single motion lifts the same account's ban across two markets that use distinct registries."
    if lido_lend.easy_track:
        pytest.skip("multi-market unban needs a second stub market; not constructible against a real deployment")

    core = lido_lend.contract("core")
    gs1 = lido_lend.contract("guardianSignals")
    market_id_1 = lido_lend.market["id"]

    # A second market registered on the core stub, with its own GuardianSignals registry.
    gs2 = GuardianSignalsStub.deploy({"from": deployer})
    controller2 = LidoLendMarketControllerStub.deploy({"from": deployer})
    controller2.setGuardianSignals(gs2, {"from": deployer})
    market_id_2 = (2).to_bytes(32, "big")
    core.setMarketController(market_id_2, controller2, {"from": deployer})

    gs1.grantRole(gs1.ACCESS_LIMITER_ROLE(), admin, {"from": admin})
    gs1.ban(market_id_1, BANNED_ACCOUNT, {"from": admin})
    gs2.ban(market_id_2, BANNED_ACCOUNT, {"from": deployer})
    assert gs1.isBanned(market_id_1, BANNED_ACCOUNT)
    assert gs2.isBanned(market_id_2, BANNED_ACCOUNT)

    factory = deployer.deploy(LidoLendUnbanGuardianSignals, trusted_caller, core)
    register_factory(factory, permission((gs1, gs1.unban), (gs2, gs2.unban)))
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32[]", "address"], [[market_id_1, market_id_2], BANNED_ACCOUNT]).hex(),
        trusted_caller,
    )

    assert not gs1.isBanned(market_id_1, BANNED_ACCOUNT)
    assert not gs2.isBanned(market_id_2, BANNED_ACCOUNT)
