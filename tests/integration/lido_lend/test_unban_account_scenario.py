import pytest
from brownie import interface, LidoLendGuardianActions, LidoLendMarketControllerStub, GuardianSignalsStub
from eth_abi import encode

BANNED_ACCOUNTS = ["0x" + "55" * 20, "0x" + "56" * 20]
ACTION = 5


def create_calldata(requests):
    payload = encode(["(address,bytes32[])[]"], [requests])
    return "0x" + encode(["uint8", "bytes"], [ACTION, payload]).hex()


def test_unban_account_multi_market_scenario(
    lido_lend, created_markets, easy_track, deployer, trusted_caller, admin, permission, register_factory, enact_motion
):
    "A motion lifts only the account-market pairs named in each request."
    if lido_lend.easy_track:
        if len(lido_lend.markets) < 2:
            raise pytest.UsageError("artifact mode requires at least two markets for the cross-market scenario")
        market1, market2 = lido_lend.markets[:2]
        gs1 = interface.GuardianSignals(market1["guardianSignals"])
        gs2 = interface.GuardianSignals(market2["guardianSignals"])
        market_id_1, market_id_2 = market1["id"], market2["id"]
        for gs in (gs1, gs2):
            gs.grantRole(gs.ACCESS_LIMITER_ROLE(), admin, {"from": admin})
        for account in BANNED_ACCOUNTS:
            gs1.ban(market_id_1, account, {"from": admin})
            gs2.ban(market_id_2, account, {"from": admin})
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
        for account in BANNED_ACCOUNTS:
            gs1.ban(market_id_1, account, {"from": admin})
            gs2.ban(market_id_2, account, {"from": deployer})
    for account in BANNED_ACCOUNTS:
        assert gs1.isBanned(market_id_1, account)
        assert gs2.isBanned(market_id_2, account)

    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, owner)
    # One permission for the facade covers every market the batch touches — no per-registry enumeration.
    register_factory(factory, permission((owner, owner.unbanGuardianSignals)))
    requests = [
        (BANNED_ACCOUNTS[0], [market_id_1]),
        (BANNED_ACCOUNTS[1], [market_id_2]),
    ]
    enact_motion(
        easy_track,
        factory,
        create_calldata(requests),
        trusted_caller,
    )

    assert not gs1.isBanned(market_id_1, BANNED_ACCOUNTS[0])
    assert not gs2.isBanned(market_id_2, BANNED_ACCOUNTS[1])
    assert gs1.isBanned(market_id_1, BANNED_ACCOUNTS[1])
    assert gs2.isBanned(market_id_2, BANNED_ACCOUNTS[0])
