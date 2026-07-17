import pytest
from eth_abi import encode
from brownie import (
    reverts,
    LidoLendUnbanGuardianSignals,
    LidoLendCoreStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    EasyTrack,
    MockERC20,
)

import constants
from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
SECOND_MARKET_ID = (2).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (3).to_bytes(32, "big")


def create_calldata(market_ids, account):
    return "0x" + encode(["bytes32[]", "address"], [market_ids, str(account)]).hex()


@pytest.fixture(scope="module")
def guardian_signals_stub(owner):
    return GuardianSignalsStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, guardian_signals_stub):
    first_controller = LidoLendMarketControllerStub.deploy({"from": owner})
    first_controller.setGuardianSignals(guardian_signals_stub, {"from": owner})

    second_controller = LidoLendMarketControllerStub.deploy({"from": owner})
    second_controller.setGuardianSignals(guardian_signals_stub, {"from": owner})

    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketController(MARKET_ID, first_controller, {"from": owner})
    core.setMarketController(SECOND_MARKET_ID, second_controller, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub):
    return LidoLendUnbanGuardianSignals.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata([MARKET_ID], stranger))


def test_create_evm_script_empty_market_ids(owner, factory, stranger):
    "Must revert with 'EMPTY_MARKETS_LIST' if no market ids were provided"
    with reverts("EMPTY_MARKETS_LIST"):
        factory.createEVMScript(owner, create_calldata([], stranger))


def test_create_evm_script_market_not_found(owner, guardian_signals_stub, factory, stranger):
    "Must revert with 'MARKET_NOT_FOUND' if the core has no controller for one of the market ids"
    # Ban on the known market so its loop iteration passes the isBanned check and the loop reaches
    # the unknown market id, where controller resolution reverts.
    guardian_signals_stub.setBanned(MARKET_ID, stranger, True, {"from": owner})
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata([MARKET_ID, UNKNOWN_MARKET_ID], stranger))


def test_create_evm_script_not_banned(owner, guardian_signals_stub, factory, stranger):
    "Must revert with message 'ACCOUNT_IS_NOT_BANNED' if the account is not currently banned on one of the markets"
    guardian_signals_stub.setBanned(MARKET_ID, stranger, True, {"from": owner})
    assert guardian_signals_stub.isBanned(MARKET_ID, stranger)
    assert not guardian_signals_stub.isBanned(SECOND_MARKET_ID, stranger)

    with reverts("ACCOUNT_IS_NOT_BANNED"):
        factory.createEVMScript(owner, create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger))


def test_create_evm_script(owner, guardian_signals_stub, factory, stranger):
    "Must create correct EVMScript when the account is currently banned on every target market"
    guardian_signals_stub.setBanned(MARKET_ID, stranger, True, {"from": owner})
    guardian_signals_stub.setBanned(SECOND_MARKET_ID, stranger, True, {"from": owner})
    assert guardian_signals_stub.isBanned(MARKET_ID, stranger)
    assert guardian_signals_stub.isBanned(SECOND_MARKET_ID, stranger)

    calldata = create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                guardian_signals_stub.address,
                guardian_signals_stub.unban.encode_input(MARKET_ID, stranger),
            ),
            (
                guardian_signals_stub.address,
                guardian_signals_stub.unban.encode_input(SECOND_MARKET_ID, stranger),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, stranger):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger)
    decoded_market_ids, decoded_account = factory.decodeEVMScriptCallData(calldata)
    assert decoded_market_ids == ["0x" + MARKET_ID.hex(), "0x" + SECOND_MARKET_ID.hex()]
    assert decoded_account == stranger


def test_resolves_registry_per_market_id(owner, stranger):
    "The target registry is resolved from each calldata marketId, so a batched script can touch distinct GuardianSignals registries."
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (11).to_bytes(32, "big"), (12).to_bytes(32, "big")
    registries = {}

    for mid in (market_a, market_b):
        gs = GuardianSignalsStub.deploy({"from": owner})
        gs.setBanned(mid, stranger, True, {"from": owner})
        controller = LidoLendMarketControllerStub.deploy({"from": owner})
        controller.setGuardianSignals(gs, {"from": owner})
        core.setMarketController(mid, controller, {"from": owner})
        registries[mid] = gs

    factory = LidoLendUnbanGuardianSignals.deploy(owner, core, {"from": owner})
    script = factory.createEVMScript(owner, create_calldata([market_a, market_b], stranger))

    gs_a, gs_b = registries[market_a], registries[market_b]
    assert script == encode_call_script(
        [
            (gs_a.address, gs_a.unban.encode_input(market_a, stranger)),
            (gs_b.address, gs_b.unban.encode_input(market_b, stranger)),
        ]
    )


def test_create_motion_rejected_if_any_target_is_unpermissioned(owner, stranger):
    "A batched motion must be rejected at createMotion when permissions cover only a subset of the resolved GuardianSignals targets."
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (21).to_bytes(32, "big"), (22).to_bytes(32, "big")
    registries = {}

    for mid in (market_a, market_b):
        gs = GuardianSignalsStub.deploy({"from": owner})
        gs.setBanned(mid, stranger, True, {"from": owner})
        controller = LidoLendMarketControllerStub.deploy({"from": owner})
        controller.setGuardianSignals(gs, {"from": owner})
        core.setMarketController(mid, controller, {"from": owner})
        registries[mid] = gs

    factory = LidoLendUnbanGuardianSignals.deploy(owner, core, {"from": owner})
    gs_a = registries[market_a]
    partial_permission = gs_a.address + gs_a.unban.signature[2:]

    # A local EasyTrack (owner as admin) suffices: createMotion's permission check runs at motion
    # CREATION and never invokes the EVMScriptExecutor (that runs only at enactment), so no Lido-fork
    # fixtures or executor wiring are needed — this keeps the whole unit file runnable on plain anvil/CI.
    ldo = MockERC20.deploy(18, {"from": owner})
    easy_track = owner.deploy(
        EasyTrack,
        ldo,
        owner,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )
    easy_track.addEVMScriptFactory(factory, partial_permission, {"from": owner})

    # Assert via `.call()` (eth_call): a reverted state-changing tx does not reliably surface its
    # revert-reason string on all dev nodes (e.g. anvil returns None), while eth_call decodes it.
    with reverts("HAS_NO_PERMISSIONS"):
        easy_track.createMotion.call(
            factory, create_calldata([market_a, market_b], stranger), {"from": owner}
        )
