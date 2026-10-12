import pytest
from brownie import reverts, LidoLendGuardianActions, LidoLendMarketManagerActions
from eth_abi import encode

GUARDIAN_A = "0x" + "a1" * 20
GUARDIAN_B = "0x" + "b2" * 20
LDO_WHALE = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"


def _envelope(action, payload):
    return "0x" + encode(["uint8", "bytes"], [action, payload]).hex()


def _add_guardian_calldata(market_id, addr):
    payload = encode(["bytes32", "address", "uint256"], [market_id, str(addr), 1])
    return _envelope(0, payload)


def _set_suspect_window_calldata(market_id, window):
    return _envelope(4, encode(["bytes32", "uint256"], [market_id, window]))


def _assert_reverts_with_reason(method, reason, *args):
    with reverts(reason):
        method.call(*args)

    # The reason is checked above: Brownie may not recover it from Anvil transaction traces.
    with reverts():
        method(*args)


@pytest.fixture
def registered_add_guardian(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory
):
    "A registered GuardianActions factory routing through the LidoLendOwner facade."
    gs = lido_lend.contract("guardianSignals")
    owner = lido_lend.contract("owner")
    gs.grantRole(gs.MANAGER_ROLE(), admin, {"from": admin})
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, owner)
    register_factory(
        factory,
        permission(
            (owner, owner.addGuardian),
            (owner, owner.setGuardiansQuorum),
            (owner, owner.removeGuardian),
            (owner, owner.replaceGuardian),
            (owner, owner.setGuardiansSuspectWindow),
            (owner, owner.unbanGuardianSignals),
        ),
    )
    return factory, gs, lido_lend.market["id"]


def test_stranger_cannot_open_motion(easy_track, registered_add_guardian, stranger):
    "createMotion by a non-trusted caller must revert (factory onlyTrustedCaller -> CALLER_IS_FORBIDDEN)."
    factory, _, market_id = registered_add_guardian
    _assert_reverts_with_reason(
        easy_track.createMotion,
        "CALLER_IS_FORBIDDEN",
        factory,
        _add_guardian_calldata(market_id, GUARDIAN_A),
        {"from": stranger},
    )


def test_unregistered_factory_cannot_open_motion(lido_lend, created_market, easy_track, deployer, trusted_caller):
    "createMotion for a factory never added to EasyTrack must revert (EVM_SCRIPT_FACTORY_NOT_FOUND)."
    factory = deployer.deploy(LidoLendGuardianActions, trusted_caller, lido_lend.contract("owner"))
    _assert_reverts_with_reason(
        easy_track.createMotion,
        "EVM_SCRIPT_FACTORY_NOT_FOUND",
        factory,
        _add_guardian_calldata(lido_lend.market["id"], GUARDIAN_A),
        {"from": trusted_caller},
    )


def test_cannot_enact_before_objection_window(
    easy_track, registered_add_guardian, trusted_caller, stranger, create_motion
):
    "enactMotion before the objection window elapses must revert (MOTION_NOT_PASSED)."
    factory, _, market_id = registered_add_guardian
    calldata = _add_guardian_calldata(market_id, GUARDIAN_A)
    _, motion_id = create_motion(easy_track, factory, calldata, trusted_caller)
    _assert_reverts_with_reason(
        easy_track.enactMotion,
        "MOTION_NOT_PASSED",
        motion_id,
        calldata,
        {"from": stranger},
    )


def test_cannot_enact_with_tampered_calldata(
    easy_track, registered_add_guardian, trusted_caller, stranger, create_motion, advance_time
):
    "enactMotion with calldata different from what was recorded at creation must revert (UNEXPECTED_EVM_SCRIPT)."
    factory, _, market_id = registered_add_guardian
    _, motion_id = create_motion(
        easy_track,
        factory,
        _add_guardian_calldata(market_id, GUARDIAN_A),
        trusted_caller,
    )
    advance_time(easy_track.motionDuration() + 100)
    _assert_reverts_with_reason(
        easy_track.enactMotion,
        "UNEXPECTED_EVM_SCRIPT",
        motion_id,
        _add_guardian_calldata(market_id, GUARDIAN_B),
        {"from": stranger},
    )


def test_cannot_enact_with_another_valid_action(
    easy_track,
    registered_add_guardian,
    trusted_caller,
    stranger,
    create_motion,
    advance_time,
):
    "A different valid action from the same grouped factory must still fail the stored EVMScript hash check."
    factory, guardian_signals, market_id = registered_add_guardian
    _, motion_id = create_motion(
        easy_track,
        factory,
        _add_guardian_calldata(market_id, GUARDIAN_A),
        trusted_caller,
    )
    new_window = 1 if guardian_signals.getSuspectWindow() != 1 else 2
    advance_time(easy_track.motionDuration() + 100)

    _assert_reverts_with_reason(
        easy_track.enactMotion,
        "UNEXPECTED_EVM_SCRIPT",
        motion_id,
        _set_suspect_window_calldata(market_id, new_window),
        {"from": stranger},
    )


def test_stale_precondition_reverts_on_enact(
    easy_track,
    registered_add_guardian,
    admin,
    trusted_caller,
    stranger,
    create_motion,
    advance_time,
):
    "If a precondition changes after creation, enactment must fail during factory revalidation."
    factory, gs, market_id = registered_add_guardian

    calldata = _add_guardian_calldata(market_id, GUARDIAN_A)
    _, motion_id = create_motion(easy_track, factory, calldata, trusted_caller)

    gs.addGuardian(GUARDIAN_A, {"from": admin})
    assert gs.isGuardian(GUARDIAN_A)

    advance_time(easy_track.motionDuration() + 100)

    _assert_reverts_with_reason(
        easy_track.enactMotion,
        "GUARDIAN_ALREADY_ADDED",
        motion_id,
        calldata,
        {"from": stranger},
    )


def test_motion_rejected_by_objection(
    easy_track,
    registered_add_guardian,
    trusted_caller,
    stranger,
    create_motion,
    advance_time,
    impersonate,
):
    "A motion objected above the 0.5%-LDO threshold is rejected and removed, so it can never be enacted."
    factory, _, market_id = registered_add_guardian
    calldata = _add_guardian_calldata(market_id, GUARDIAN_A)
    existing_motion_ids = {motion[0] for motion in easy_track.getMotions()}
    _, motion_id = create_motion(easy_track, factory, calldata, trusted_caller)
    assert {motion[0] for motion in easy_track.getMotions()} == existing_motion_ids | {motion_id}

    whale = impersonate(LDO_WHALE)
    easy_track.objectToMotion(motion_id, {"from": whale})

    assert {motion[0] for motion in easy_track.getMotions()} == existing_motion_ids
    advance_time(easy_track.motionDuration() + 100)
    _assert_reverts_with_reason(
        easy_track.enactMotion,
        "MOTION_NOT_FOUND",
        motion_id,
        calldata,
        {"from": stranger},
    )


def test_factory_with_wrong_permission_rejects_motion(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory
):
    "A factory registered with a permission for a different call must have its motions rejected (HAS_NO_PERMISSIONS)."
    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendMarketManagerActions, trusted_caller, owner)
    # Right target (facade), wrong selector: SetSupplyCap emits setMarketSupplyCap, permission lists another call.
    register_factory(factory, permission((owner, owner.setMarketSettlementConfig)))
    _assert_reverts_with_reason(
        easy_track.createMotion,
        "HAS_NO_PERMISSIONS",
        factory,
        _envelope(3, encode(["bytes32", "uint256"], [lido_lend.market["id"], 10**24])),
        {"from": trusted_caller},
    )
