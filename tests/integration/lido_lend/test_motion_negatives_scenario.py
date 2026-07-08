
import pytest
from brownie import reverts, accounts, web3, LidoLendAddGuardian, LidoLendSetSupplyCap
from eth_abi import encode

GUARDIAN_A = "0x" + "a1" * 20
GUARDIAN_B = "0x" + "b2" * 20
LDO_WHALE = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"


def _calldata(market_id, addr):
    return "0x" + encode(["bytes32", "address"], [market_id, str(addr)]).hex()


@pytest.fixture
def registered_add_guardian(
    lido_lend, created_market, easy_track, deployer, trusted_caller, admin, permission, register_factory
):
    "A registered AddGuardian factory over the market's GuardianSignals registry (resolved via the core)."
    gs = lido_lend.contract("guardianSignals")
    gs.grantRole(gs.MANAGER_ROLE(), admin, {"from": admin})
    factory = deployer.deploy(LidoLendAddGuardian, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((gs, gs.addGuardian)))
    return factory, gs, lido_lend.market["id"]


def test_stranger_cannot_open_motion(easy_track, registered_add_guardian, stranger):
    "createMotion by a non-trusted caller must revert (factory onlyTrustedCaller -> CALLER_IS_FORBIDDEN)."
    factory, _, market_id = registered_add_guardian
    with reverts():
        easy_track.createMotion(factory, _calldata(market_id, GUARDIAN_A), {"from": stranger})


def test_unregistered_factory_cannot_open_motion(lido_lend, created_market, easy_track, deployer, trusted_caller):
    "createMotion for a factory never added to EasyTrack must revert (EVM_SCRIPT_FACTORY_NOT_FOUND)."
    factory = deployer.deploy(LidoLendAddGuardian, trusted_caller, lido_lend.contract("core"))
    with reverts():
        easy_track.createMotion(factory, _calldata(lido_lend.market["id"], GUARDIAN_A), {"from": trusted_caller})


def test_cannot_enact_before_objection_window(easy_track, registered_add_guardian, trusted_caller, stranger):
    "enactMotion before the objection window elapses must revert (MOTION_NOT_PASSED)."
    factory, _, market_id = registered_add_guardian
    tx = easy_track.createMotion(factory, _calldata(market_id, GUARDIAN_A), {"from": trusted_caller})
    motion_id = tx.events["MotionCreated"]["_motionId"]
    with reverts():
        easy_track.enactMotion(motion_id, tx.events["MotionCreated"]["_evmScriptCallData"], {"from": stranger})


def test_cannot_enact_with_tampered_calldata(easy_track, registered_add_guardian, trusted_caller, stranger, advance_time):
    "enactMotion with calldata different from what was recorded at creation must revert (UNEXPECTED_EVM_SCRIPT)."
    factory, _, market_id = registered_add_guardian
    tx = easy_track.createMotion(factory, _calldata(market_id, GUARDIAN_A), {"from": trusted_caller})
    motion_id = tx.events["MotionCreated"]["_motionId"]
    advance_time(easy_track.motionDuration() + 100)
    with reverts():
        easy_track.enactMotion(motion_id, _calldata(market_id, GUARDIAN_B), {"from": stranger})


def test_stale_precondition_reverts_on_enact(easy_track, registered_add_guardian, admin, trusted_caller, stranger, advance_time):
    "If the factory's precondition is invalidated between creation and enactment, the stored script must revert at the target."
    factory, gs, market_id = registered_add_guardian

    tx = easy_track.createMotion(factory, _calldata(market_id, GUARDIAN_A), {"from": trusted_caller})
    motion_id = tx.events["MotionCreated"]["_motionId"]

    gs.addGuardian(GUARDIAN_A, {"from": admin})
    assert gs.isGuardian(GUARDIAN_A)

    advance_time(easy_track.motionDuration() + 100)

    with reverts():
        easy_track.enactMotion(motion_id, tx.events["MotionCreated"]["_evmScriptCallData"], {"from": stranger})


def test_motion_rejected_by_objection(easy_track, registered_add_guardian, trusted_caller, stranger, advance_time):
    "A motion objected above the 0.5%-LDO threshold is rejected and removed, so it can never be enacted."
    factory, _, market_id = registered_add_guardian
    tx = easy_track.createMotion(factory, _calldata(market_id, GUARDIAN_A), {"from": trusted_caller})
    motion_id = tx.events["MotionCreated"]["_motionId"]
    assert len(easy_track.getMotions()) == 1

    whale = accounts.at(LDO_WHALE, force=True)
    web3.provider.make_request("anvil_setBalance", [whale.address, hex(10**22)])
    easy_track.objectToMotion(motion_id, {"from": whale})

    assert len(easy_track.getMotions()) == 0
    advance_time(easy_track.motionDuration() + 100)
    with reverts():
        easy_track.enactMotion(motion_id, tx.events["MotionCreated"]["_evmScriptCallData"], {"from": stranger})


def test_factory_with_wrong_permission_rejects_motion(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory
):
    "A factory registered with a permission for a different call must have its motions rejected (HAS_NO_PERMISSIONS)."
    controller = lido_lend.contract("controller")
    factory = deployer.deploy(LidoLendSetSupplyCap, trusted_caller, lido_lend.contract("core"))
    register_factory(factory, permission((controller, controller.setSettlementConfig)))
    with reverts():
        easy_track.createMotion(
            factory, "0x" + encode(["bytes32", "uint256"], [lido_lend.market["id"], 10**24]).hex(), {"from": trusted_caller}
        )


def test_motion_for_unpermissioned_target_rejected(
    lido_lend, created_market, easy_track, deployer, trusted_caller, permission, register_factory
):
    "Per-market scoping backstop: a domain-scoped factory reaches only the target its permission lists. Registered with the RIGHT selector but a target that is NOT this market's resolved registry, its motion is rejected at createMotion (HAS_NO_PERMISSIONS). Since the factory resolves the registry per calldata marketId, this is exactly what stops a factory permissioned for one market from acting on another (whose resolved registry differs). A literal two-market check needs a second market on the deploy (single-market fork here)."
    gs = lido_lend.contract("guardianSignals")
    factory = deployer.deploy(LidoLendAddGuardian, trusted_caller, lido_lend.contract("core"))
    # Right selector (addGuardian), wrong target (controller, standing in for another market's registry).
    register_factory(factory, permission((lido_lend.contract("controller"), gs.addGuardian)))
    with reverts():
        easy_track.createMotion(factory, _calldata(lido_lend.market["id"], GUARDIAN_A), {"from": trusted_caller})
