import pytest
from brownie import reverts, LidoLendAddGuardian, LidoLendSetSupplyCap
from eth_abi import encode

GUARDIAN_A = "0x" + "a1" * 20
GUARDIAN_B = "0x" + "b2" * 20
LDO_WHALE = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"


def _calldata(market_id, addr):
    return "0x" + encode(["bytes32", "address", "uint256"], [market_id, str(addr), 1]).hex()


@pytest.fixture
def registered_add_guardian(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory
):
    "A registered AddGuardian factory routing through the LidoLendOwner facade (resolves the registry by id)."
    gs = lido_lend.contract("guardianSignals")
    owner = lido_lend.contract("owner")
    gs.grantRole(gs.MANAGER_ROLE(), admin, {"from": admin})
    factory = deployer.deploy(LidoLendAddGuardian, trusted_caller, owner)
    register_factory(
        factory,
        permission((owner, owner.addGuardian), (owner, owner.setGuardiansQuorum)),
    )
    return factory, gs, lido_lend.market["id"]


def test_stranger_cannot_open_motion(easy_track, registered_add_guardian, stranger):
    "createMotion by a non-trusted caller must revert (factory onlyTrustedCaller -> CALLER_IS_FORBIDDEN)."
    factory, _, market_id = registered_add_guardian
    with reverts():
        easy_track.createMotion(factory, _calldata(market_id, GUARDIAN_A), {"from": stranger})


def test_unregistered_factory_cannot_open_motion(lido_lend, created_market, easy_track, deployer, trusted_caller):
    "createMotion for a factory never added to EasyTrack must revert (EVM_SCRIPT_FACTORY_NOT_FOUND)."
    factory = deployer.deploy(LidoLendAddGuardian, trusted_caller, lido_lend.contract("owner"))
    with reverts():
        easy_track.createMotion(factory, _calldata(lido_lend.market["id"], GUARDIAN_A), {"from": trusted_caller})


def test_cannot_enact_before_objection_window(
    easy_track, registered_add_guardian, trusted_caller, stranger, create_motion
):
    "enactMotion before the objection window elapses must revert (MOTION_NOT_PASSED)."
    factory, _, market_id = registered_add_guardian
    calldata = _calldata(market_id, GUARDIAN_A)
    _, motion_id = create_motion(easy_track, factory, calldata, trusted_caller)
    with reverts():
        easy_track.enactMotion(motion_id, calldata, {"from": stranger})


def test_cannot_enact_with_tampered_calldata(
    easy_track, registered_add_guardian, trusted_caller, stranger, create_motion, advance_time
):
    "enactMotion with calldata different from what was recorded at creation must revert (UNEXPECTED_EVM_SCRIPT)."
    factory, _, market_id = registered_add_guardian
    _, motion_id = create_motion(easy_track, factory, _calldata(market_id, GUARDIAN_A), trusted_caller)
    advance_time(easy_track.motionDuration() + 100)
    with reverts():
        easy_track.enactMotion(motion_id, _calldata(market_id, GUARDIAN_B), {"from": stranger})


def test_stale_precondition_reverts_on_enact(
    easy_track,
    registered_add_guardian,
    admin,
    trusted_caller,
    stranger,
    create_motion,
    advance_time,
):
    "If the factory's precondition is invalidated between creation and enactment, the stored script must revert at the target."
    factory, gs, market_id = registered_add_guardian

    calldata = _calldata(market_id, GUARDIAN_A)
    _, motion_id = create_motion(easy_track, factory, calldata, trusted_caller)

    gs.addGuardian(GUARDIAN_A, {"from": admin})
    assert gs.isGuardian(GUARDIAN_A)

    advance_time(easy_track.motionDuration() + 100)

    with reverts():
        easy_track.enactMotion(motion_id, calldata, {"from": stranger})


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
    calldata = _calldata(market_id, GUARDIAN_A)
    existing_motion_ids = {motion[0] for motion in easy_track.getMotions()}
    _, motion_id = create_motion(easy_track, factory, calldata, trusted_caller)
    assert {motion[0] for motion in easy_track.getMotions()} == existing_motion_ids | {motion_id}

    whale = impersonate(LDO_WHALE)
    easy_track.objectToMotion(motion_id, {"from": whale})

    assert {motion[0] for motion in easy_track.getMotions()} == existing_motion_ids
    advance_time(easy_track.motionDuration() + 100)
    with reverts():
        easy_track.enactMotion(motion_id, calldata, {"from": stranger})


def test_factory_with_wrong_permission_rejects_motion(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory
):
    "A factory registered with a permission for a different call must have its motions rejected (HAS_NO_PERMISSIONS)."
    owner = lido_lend.contract("owner")
    factory = deployer.deploy(LidoLendSetSupplyCap, trusted_caller, owner)
    # Right target (facade), wrong selector: SetSupplyCap emits setMarketSupplyCap, permission lists another call.
    register_factory(factory, permission((owner, owner.setMarketSettlementConfig)))
    with reverts():
        easy_track.createMotion(
            factory,
            "0x" + encode(["bytes32", "uint256"], [lido_lend.market["id"], 10**24]).hex(),
            {"from": trusted_caller},
        )
