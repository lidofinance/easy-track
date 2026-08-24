import pytest
from brownie import interface, LidoLendGuardianActions, LidoLendMarketControllerStub, GuardianSignalsStub
from eth_abi import encode

BANNED_ACCOUNT = "0x" + "55" * 20
SECOND_BANNED_ACCOUNT = "0x" + "56" * 20
ACTION = 5


def create_calldata(market_ids, accounts):
    payload = encode(["bytes32[]", "address[]"], [market_ids, accounts])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_unban_account_scenario(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A Manager Committee motion lifts a ban previously latched on the market's GuardianSignals registry."
    gs = lido_lend.contract("guardianSignals")
    market_id = lido_lend.market["id"]

    gs.grantRole(gs.ACCESS_LIMITER_ROLE(), admin, {"from": admin})
    gs.ban(market_id, BANNED_ACCOUNT, {"from": admin})
    assert gs.isBanned(market_id, BANNED_ACCOUNT)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, owner)
    register_factory(factory, permission((owner, owner.unbanGuardianSignals)))
    enact_motion(
        easy_track,
        factory,
        create_calldata([market_id], [BANNED_ACCOUNT]),
        trusted_caller,
    )

    assert not gs.isBanned(market_id, BANNED_ACCOUNT)


def test_unban_account_multi_market_scenario(
    lido_lend, created_markets, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A single motion lifts different accounts' bans across two markets, including a shared-registry topology."
    if lido_lend.easy_track:
        if len(lido_lend.markets) < 2:
            raise pytest.UsageError("artifact mode requires at least two markets for the cross-market scenario")
        market1, market2 = lido_lend.markets[:2]
        gs1 = interface.GuardianSignals(market1["guardianSignals"])
        gs2 = interface.GuardianSignals(market2["guardianSignals"])
        market_id_1, market_id_2 = market1["id"], market2["id"]
        for gs in (gs1, gs2):
            gs.grantRole(gs.ACCESS_LIMITER_ROLE(), admin, {"from": admin})
        gs1.ban(market_id_1, BANNED_ACCOUNT, {"from": admin})
        gs2.ban(market_id_2, SECOND_BANNED_ACCOUNT, {"from": admin})
    else:
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
        gs2.ban(market_id_2, SECOND_BANNED_ACCOUNT, {"from": deployer})
    assert gs1.isBanned(market_id_1, BANNED_ACCOUNT)
    assert gs2.isBanned(market_id_2, SECOND_BANNED_ACCOUNT)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, owner)
    # One permission for the facade covers every market the batch touches — no per-registry enumeration.
    register_factory(factory, permission((owner, owner.unbanGuardianSignals)))
    enact_motion(
        easy_track,
        factory,
        create_calldata(
            [market_id_1, market_id_2],
            [BANNED_ACCOUNT, SECOND_BANNED_ACCOUNT],
        ),
        trusted_caller,
    )

    assert not gs1.isBanned(market_id_1, BANNED_ACCOUNT)
    assert not gs2.isBanned(market_id_2, SECOND_BANNED_ACCOUNT)
