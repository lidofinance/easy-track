import pytest
import constants
from brownie.network.state import Chain
from brownie import reverts, ZERO_ADDRESS
from utils.evm_script import encode_call_script
from utils.test_helpers import (
    access_revert_message,
    CANCEL_ROLE,
    PAUSE_ROLE,
    UNPAUSE_ROLE,
)


def test_deploy(owner, ldo, voting, EasyTrack):
    "Must deploy contract with correct data"
    easy_track = owner.deploy(
        EasyTrack,
        ldo,
        voting,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )

    assert not easy_track.paused()
    assert easy_track.governanceToken() == ldo
    assert easy_track.evmScriptExecutor() == ZERO_ADDRESS
    assert easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), voting)
    assert easy_track.hasRole(easy_track.PAUSE_ROLE(), voting)
    assert easy_track.hasRole(easy_track.UNPAUSE_ROLE(), voting)
    assert easy_track.hasRole(easy_track.CANCEL_ROLE(), voting)


########
# Create Motion
########


def test_create_motion_when_paused(voting, stranger, easy_track):
    "Must revert with message 'Pausable: paused' if called on paused EasyTrack"
    easy_track.pause({"from": voting})
    assert easy_track.paused()
    with reverts("Pausable: paused"):
        easy_track.createMotion(ZERO_ADDRESS, b"", {"from": stranger})


def test_create_motion_evm_script_factory_not_found(owner, stranger, easy_track):
    "Must revert with message 'EVM_SCRIPT_FACTORY_NOT_FOUND'"
    "if called with not registered EVM Script factory"
    with reverts("EVM_SCRIPT_FACTORY_NOT_FOUND"):
        easy_track.createMotion(stranger, b"", {"from": owner})


def test_create_motion_has_no_permissions(voting, stranger, easy_track, evm_script_factory_stub):
    "Must revert with message 'HAS_NO_PERMISSIONS' if evm script"
    "tries to call method not listed in permissions"
    wrong_permissions = ZERO_ADDRESS + "11111111"
    easy_track.addEVMScriptFactory(evm_script_factory_stub, wrong_permissions, {"from": voting})
    assert evm_script_factory_stub.DEFAULT_PERMISSIONS() != wrong_permissions
    with reverts("HAS_NO_PERMISSIONS"):
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})


def test_create_motion_motions_limit_reached(voting, stranger, easy_track, evm_script_factory_stub):
    "Must revert with message 'MOTIONS_LIMIT_REACHED' when motionsCountLimit reached"
    easy_track.setMotionsCountLimit(1, {"from": voting})
    assert easy_track.motionsCountLimit() == 1

    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert len(easy_track.getMotions()) == 0
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})
    assert len(easy_track.getMotions()) == 1
    with reverts("MOTIONS_LIMIT_REACHED"):
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})


def test_create_motion(owner, voting, easy_track, evm_script_factory_stub):
    "Must create new motion with correct data and emit"
    "MotionCreated event if called by easy track"
    chain = Chain()

    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create motion
    call_data = "0xaabbccddeeff"
    tx = easy_track.createMotion(evm_script_factory_stub, call_data, {"from": owner})

    # validate events
    assert len(tx.events) == 1
    assert tx.events["MotionCreated"]["_motionId"] == 1
    assert tx.events["MotionCreated"]["_creator"] == owner
    assert tx.events["MotionCreated"]["_evmScriptFactory"] == evm_script_factory_stub
    assert tx.events["MotionCreated"]["_evmScriptCallData"] == call_data
    assert tx.events["MotionCreated"]["_evmScript"] == evm_script_factory_stub.DEFAULT_EVM_SCRIPT()

    # validate motion data
    motions = easy_track.getMotions()
    assert len(motions) == 1
    new_motion = motions[0]

    assert new_motion[0] == 1  # id
    assert new_motion[1] == evm_script_factory_stub  # evmScriptFactory
    assert new_motion[2] == owner  # creator
    assert new_motion[3] == constants.MIN_MOTION_DURATION  # duration
    assert new_motion[4] == chain[-1].timestamp  # startDate
    assert new_motion[5] == chain[-1].number  # snapshotBlock
    assert new_motion[6] == constants.DEFAULT_OBJECTIONS_THRESHOLD  # objectionsThreshold
    assert new_motion[7] == 0  # objectionsAmount
    assert new_motion[8] == evm_script_factory_stub.DEFAULT_EVM_SCRIPT_HASH()  # evmScriptHash


########
# CANCEL MOTION
########


def test_cancel_motion_not_found(owner, easy_track):
    "Must revert with message 'MOTION_NOT_FOUND' if called with not existed motion id"
    with reverts("MOTION_NOT_FOUND"):
        easy_track.cancelMotion(1, {"from": owner})


def test_cancel_motion_not_creator(owner, voting, stranger, easy_track, evm_script_factory_stub):
    "Must revert with message 'NOT_CREATOR' if canceled not by owner"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion by owner
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    assert len(easy_track.getMotions()) == 1

    # try to cancel by stranger
    with reverts("NOT_CREATOR"):
        easy_track.cancelMotion(1, {"from": stranger})


def test_cancel_motion(voting, stranger, easy_track, evm_script_factory_stub):
    "Must remove motion from list of active motions and emit MotionCanceled(_motionId)"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    # cancel motion by same user
    tx = easy_track.cancelMotion(motions[0][0], {"from": stranger})

    # validate motion was canceled
    assert len(easy_track.getMotions()) == 0

    # validate event
    assert len(tx.events) == 1
    assert tx.events["MotionCanceled"]["_motionId"] == motions[0][0]


def test_cancel_motion_in_random_order(owner, voting, easy_track, evm_script_factory_stub):
    "Must remove correct motions from list of active motions"
    "whe cancelMotion called with motion id in random order"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motions
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    motions = easy_track.getMotions()
    assert len(motions) == 3
    assert motions[0][0] == 1
    assert motions[1][0] == 2
    assert motions[2][0] == 3

    easy_track.cancelMotion(2, {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 2
    assert motions[0][0] == 1
    assert motions[1][0] == 3

    easy_track.cancelMotion(1, {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1
    assert motions[0][0] == 3

    easy_track.cancelMotion(3, {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 0


########
# ENACT MOTION
########


def test_enact_motion_motion_not_found(owner, easy_track):
    "Must revert with message 'MOTION_NOT_FOUND' if called with not existed motion id"
    with reverts("MOTION_NOT_FOUND"):
        easy_track.enactMotion(1, b"", {"from": owner})


def test_enact_motion_when_paused(stranger, voting, easy_track):
    "Must revert with message 'Pausable: paused' if called on paused EasyTrack"
    easy_track.pause({"from": voting})
    assert easy_track.paused()
    with reverts("Pausable: paused"):
        easy_track.enactMotion(1, b"", {"from": stranger})


def test_enact_motion_when_motion_not_passed(owner, voting, easy_track, evm_script_factory_stub):
    "Must revert with message 'MOTION_NOT_PASSED' if called with motion id"
    "created less than motionDuration time ago"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    tx = easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    with reverts("MOTION_NOT_PASSED"):
        easy_track.enactMotion(
            motions[0][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": owner},
        )


def test_enact_motion_unexpected_evm_script(owner, voting, easy_track, evm_script_factory_stub):
    "Must revert with message 'UNEXPECTED_EVM_SCRIPT' when hash of enact script"
    "not equal to script created on motion creation step"
    # add evm script factory to create motions
    permissions = evm_script_factory_stub.address + evm_script_factory_stub.setEVMScript.signature[2:]
    easy_track.addEVMScriptFactory(evm_script_factory_stub, permissions, {"from": voting})
    evm_script_factory_stub.setEVMScript(
        encode_call_script(
            [
                (
                    evm_script_factory_stub.address,
                    evm_script_factory_stub.setEVMScript.encode_input(b""),
                )
            ]
        )
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    tx = easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain = Chain()
    chain.sleep(constants.MIN_MOTION_DURATION + 1)

    # replace evm script with different params to change evm script hash
    evm_script_factory_stub.setEVMScript(
        encode_call_script(
            [
                (
                    evm_script_factory_stub.address,
                    evm_script_factory_stub.setEVMScript.encode_input("0x001122"),
                )
            ]
        )
    )

    with reverts("UNEXPECTED_EVM_SCRIPT"):
        easy_track.enactMotion(
            motions[0][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": owner},
        )


def test_enact_motion(owner, voting, easy_track, evm_script_factory_stub, evm_script_executor_stub):
    "Must remove motion from list of active motions, execute EVM script created by EVMScriptFactory"
    "contained in created motion and emits event MotionEnacted(_moitonId)"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    easy_track.setEVMScriptExecutor(evm_script_executor_stub, {"from": voting})

    # create new motion
    tx = easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    # wait to make motion enactable
    chain = Chain()
    chain.sleep(constants.MIN_MOTION_DURATION + 1)

    # validate that evm_script_executor_stub wasn't called earlier
    assert evm_script_executor_stub.evmScript() == "0x"

    # enact motion
    tx = easy_track.enactMotion(motions[0][0], tx.events["MotionCreated"]["_evmScriptCallData"], {"from": owner})
    # validate that motion was removed from list of active motions
    assert len(easy_track.getMotions()) == 0

    # validate events
    assert len(tx.events) == 1
    assert tx.events["MotionEnacted"]["_motionId"] == motions[0][0]

    # validate that was passed correct evm script to evm_script_executor_stub
    assert evm_script_executor_stub.evmScript() == evm_script_factory_stub.DEFAULT_EVM_SCRIPT()


########
# OBJECT TO MOTION
########


def test_object_to_motion_motion_not_found(owner, easy_track):
    "Must revert with message 'MOTION_NOT_FOUND' if called with not existed motion id"
    with reverts("MOTION_NOT_FOUND"):
        easy_track.objectToMotion(1, {"from": owner})


@pytest.mark.usefixtures("distribute_holder_balance")
def test_object_to_motion_multiple_times(
    owner,
    voting,
    ldo_holders,
    easy_track,
    evm_script_factory_stub,
):
    "Must revert with message: 'ALREADY_OBJECTED' if sender already objected the motion with the given id"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    # send objection multiple times
    easy_track.objectToMotion(1, {"from": ldo_holders[0]})
    assert easy_track.objections(1, ldo_holders[0])

    with reverts("ALREADY_OBJECTED"):
        easy_track.objectToMotion(1, {"from": ldo_holders[0]})


def test_object_to_motion_not_ldo_holder(
    owner, voting, stranger, ldo_holders, ldo, easy_track, evm_script_factory_stub
):
    "Must revert with message: 'NOT_ENOUGH_BALANCE' when the sender"
    "had no governance token at the block where motion was created"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    # send objection from user without ldo
    assert ldo.balanceOf(stranger) == 0
    with reverts("NOT_ENOUGH_BALANCE"):
        easy_track.objectToMotion(1, {"from": stranger})


def test_object_to_motion_by_tokens_holder(
    owner,
    voting,
    ldo_holders,
    ldo,
    easy_track,
    evm_script_factory_stub,
    distribute_holder_balance,
):
    "Must increase motion objections on correct amount and"
    "emit ObjectionSent(_motionId,_objector,_weight,_newObjectionsAmount,_newObjectionsAmountPct) event"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    # send objection from ldo holder
    tx = easy_track.objectToMotion(1, {"from": ldo_holders[0]})

    total_supply = ldo.totalSupply()
    holder_balance = ldo.balanceOf(ldo_holders[0])
    holder_part = 10000 * holder_balance / total_supply

    motion = easy_track.getMotion(1)

    assert motion[7] == holder_balance  # objectionsAmount

    # validate events
    assert len(tx.events) == 1
    assert tx.events["MotionObjected"]["_motionId"] == motion[0]
    assert tx.events["MotionObjected"]["_objector"] == ldo_holders[0]
    assert tx.events["MotionObjected"]["_weight"] == holder_balance
    assert tx.events["MotionObjected"]["_newObjectionsAmount"] == motion[7]  # objectionsAmount
    assert tx.events["MotionObjected"]["_newObjectionsAmountPct"] == holder_part  # objectionsAmountPct


@pytest.mark.usefixtures("distribute_holder_balance")
def test_object_to_motion_rejected(
    owner,
    voting,
    ldo_holders,
    ldo,
    easy_track,
    evm_script_factory_stub,
):
    "Must remove motion from list of active motions"
    "and emit ObjectionSent(_motionId,_objector,_weight,_newObjectionsAmount,_newObjectionsAmountPct)"
    "and MotionRejected(_motionId) events"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    # send objections to pass threshold
    easy_track.objectToMotion(1, {"from": ldo_holders[0]})  # 0.2 % objections
    easy_track.objectToMotion(1, {"from": ldo_holders[1]})  # 0.4 % objections
    assert len(easy_track.getMotions()) == 1
    tx = easy_track.objectToMotion(1, {"from": ldo_holders[2]})  # 0.6 % objections
    assert len(easy_track.getMotions()) == 0

    objections_amount = ldo.balanceOf(ldo_holders[0]) + ldo.balanceOf(ldo_holders[1]) + ldo.balanceOf(ldo_holders[2])
    objections_amount_pct = 10000 * objections_amount / ldo.totalSupply()

    # validate that events was emitted
    assert len(tx.events) == 2
    assert tx.events["MotionObjected"]["_motionId"] == 1
    assert tx.events["MotionObjected"]["_objector"] == ldo_holders[2]
    assert tx.events["MotionObjected"]["_weight"] == ldo.balanceOf(ldo_holders[2])
    assert tx.events["MotionObjected"]["_newObjectionsAmount"] == objections_amount
    assert tx.events["MotionObjected"]["_newObjectionsAmountPct"] == objections_amount_pct

    assert tx.events["MotionRejected"]["_motionId"] == 1


def test_object_to_motion_edge_case(owner, stranger, agent, ldo, voting, easy_track, evm_script_factory_stub):
    "Must reject motion only if objections threshold was reached"
    objections_threshold_amount = int(easy_track.objectionsThreshold() * ldo.totalSupply() // 10000) - 1
    ldo.transfer(owner, objections_threshold_amount, {"from": agent})
    ldo.transfer(stranger, 1, {"from": agent})

    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    # motion must stay while objections threshold wasn't reached
    easy_track.objectToMotion(1, {"from": owner})
    assert len(easy_track.getMotions()) == 1

    # motion must become rejected after objections threshold reached
    easy_track.objectToMotion(1, {"from": stranger})
    assert len(easy_track.getMotions()) == 0


########
# CANCEL MOTIONS
########


def test_cancel_motions_called_without_permissions(stranger, easy_track):
    "Must revert with correct Access Control message if called"
    "by address without role 'CANCEL_ROLE'"
    with reverts(access_revert_message(stranger, CANCEL_ROLE)):
        easy_track.cancelMotions([], {"from": stranger})


def test_cancel_motions(
    owner,
    voting,
    easy_track,
    evm_script_factory_stub,
):
    "Must cancel all motions in the list. Emits MotionCanceled(_motionId) event for each canceled motion."
    "If motion with passed id doesn't exists skip it and doesn't emit event"

    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )

    # create new motions
    for _ in range(5):
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    motion_ids_to_cancel = [1, 3, 5]

    # check that motions exists before cancel
    for motionId in range(1, 6):
        easy_track.getMotion(motionId)  # must not fail then motion exists

    # cancel motions including not existed ids
    tx = easy_track.cancelMotions([6, 7] + motion_ids_to_cancel, {"from": voting})

    motions = easy_track.getMotions()
    assert len(motions) == 2
    assert motions[0][0] == 4
    assert motions[1][0] == 2

    assert len(tx.events["MotionCanceled"]) == 3
    for idx, motion_id in enumerate(motion_ids_to_cancel):
        assert tx.events["MotionCanceled"][idx]["_motionId"] == motion_id


########
# CANCEL ALL MOTIONS
########


def test_cancel_all_motions_called_by_stranger(stranger, easy_track):
    "Must revert with correct Access Control message if called"
    "by address without role 'CANCEL_ROLE'"
    with reverts(access_revert_message(stranger, CANCEL_ROLE)):
        easy_track.cancelAllMotions({"from": stranger})


def test_cancel_all_motions(owner, voting, easy_track, evm_script_factory_stub):
    "Must cancel all active motions. Emits MotionCanceled(_motionId) event for each canceled motion"
    # add evm script factory to create motions
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub,
        evm_script_factory_stub.DEFAULT_PERMISSIONS(),
        {"from": voting},
    )

    # create new motions
    for _ in range(5):
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    # check that motions exists before cancel
    for motionId in range(1, 6):
        easy_track.getMotion(motionId)  # must not fail then motion exists

    # cancel all motions
    tx = easy_track.cancelAllMotions({"from": voting})

    assert len(tx.events["MotionCanceled"]) == 5
    for idx, motion_id in enumerate(reversed(range(1, 6))):
        assert tx.events["MotionCanceled"][idx]["_motionId"] == motion_id


########
# SET EVM SCRIPT EXECUTOR
########


def test_set_evm_script_executor_called_by_stranger(stranger, easy_track):
    "Must revert with correct Access Control message if called"
    "by address without role 'DEFAULT_ADMIN_ROLE'"
    with reverts(access_revert_message(stranger)):
        easy_track.setEVMScriptExecutor(ZERO_ADDRESS, {"from": stranger})


def test_set_evm_script_executor_called_by_owner(voting, easy_track, evm_script_executor, evm_script_executor_stub):
    "Must set new EVMScriptExecutor and emit EVMScriptExecutorChanged(_evmScriptExecutor) event"

    assert easy_track.evmScriptExecutor() == evm_script_executor
    tx = easy_track.setEVMScriptExecutor(evm_script_executor_stub, {"from": voting})
    assert tx.events["EVMScriptExecutorChanged"]["_evmScriptExecutor"] == evm_script_executor_stub
    assert easy_track.evmScriptExecutor() == evm_script_executor_stub


########
# PAUSE
########


def test_pause_called_without_permissions(stranger, easy_track):
    "Must revert with correct Access Control message if called"
    "by address without role 'PAUSE_ROLE'"
    assert not easy_track.paused()
    with reverts(access_revert_message(stranger, PAUSE_ROLE)):
        easy_track.pause({"from": stranger})
    assert not easy_track.paused()


def test_pause_called_with_permissions(voting, easy_track):
    "Must pause easy track and emit Paused(account) event"
    assert not easy_track.paused()
    tx = easy_track.pause({"from": voting})
    assert easy_track.paused()
    assert len(tx.events) == 1
    assert tx.events["Paused"]["account"] == voting


def test_pause_called_when_paused(voting, easy_track):
    "Must revert with message 'Pausable: paused'"
    assert not easy_track.paused()
    easy_track.pause({"from": voting})
    assert easy_track.paused()
    with reverts("Pausable: paused"):
        easy_track.pause({"from": voting})


########
# UNPAUSE
########


def test_unpause_called_without_permissions(voting, stranger, easy_track):
    "Must revert with correct Access Control message if called"
    "by address without role 'UNPAUSE_ROLE'"
    easy_track.pause({"from": voting})
    assert easy_track.paused()
    with reverts(access_revert_message(stranger, UNPAUSE_ROLE)):
        easy_track.unpause({"from": stranger})
    assert easy_track.paused()


def test_unpause_called_when_not_paused(voting, easy_track):
    "Must revert with message 'Pausable: not paused'"
    assert not easy_track.paused()
    with reverts("Pausable: not paused"):
        easy_track.unpause({"from": voting})


def test_unpause_called_with_permissions(voting, easy_track):
    "Must unpause easy track and emit Unpaused(account) event"
    easy_track.pause({"from": voting})
    assert easy_track.paused()
    tx = easy_track.unpause({"from": voting})
    assert not easy_track.paused()
    assert len(tx.events) == 1
    assert tx.events["Unpaused"]["account"] == voting


########
# CAN OBJECT TO MOTION
########


@pytest.mark.usefixtures("distribute_holder_balance")
def test_can_object_to_motion(
    owner,
    voting,
    stranger,
    ldo_holders,
    easy_track,
    evm_script_factory_stub,
):
    "Must return False if caller has no governance tokens or if he has already voted."
    "Returns True in other cases"

    # add evm script factory to create motions§
    permissions = evm_script_factory_stub.address + evm_script_factory_stub.setEVMScript.signature[2:]
    easy_track.addEVMScriptFactory(evm_script_factory_stub, permissions, {"from": voting})
    evm_script = encode_call_script(
        [
            (
                evm_script_factory_stub.address,
                evm_script_factory_stub.setEVMScript.encode_input(b""),
            )
        ]
    )
    evm_script_factory_stub.setEVMScript(evm_script)

    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    # create new motion
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})

    assert not easy_track.canObjectToMotion(1, stranger)
    assert easy_track.canObjectToMotion(1, ldo_holders[0])
    easy_track.objectToMotion(1, {"from": ldo_holders[0]})
    assert not easy_track.canObjectToMotion(1, ldo_holders[0])
