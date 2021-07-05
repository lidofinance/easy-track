import random
import pytest
import hashlib

from brownie.network.state import Chain
from brownie import (
    Contract,
    ContractProxy,
    EasyTrack,
    accounts,
    reverts,
    ZERO_ADDRESS,
    web3,
)
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants

CANCEL_ROLE = "0x9f959e00d95122f5cbd677010436cf273ef535b86b056afc172852144b9491d7"
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"
UNPAUSE_ROLE = "0x265b220c5a8891efdd9e1b1b7fa72f257bd5169f8d87e319cf3dad6ff52b94ae"
DEFAULT_ADMIN_ROLE = (
    "0x0000000000000000000000000000000000000000000000000000000000000000"
)
PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"


def test_deploy(owner, ldo_token, voting):
    logic = owner.deploy(EasyTrack)
    proxy = owner.deploy(
        ContractProxy,
        logic,
        logic.__EasyTrackStorage_init.encode_input(ldo_token, voting),
    )
    assert proxy.implementation() == logic
    easy_track = Contract.from_abi("EasyTrackProxied", proxy, EasyTrack.abi)

    assert not easy_track.paused()
    assert easy_track.governanceToken() == ldo_token
    assert easy_track.evmScriptExecutor() == ZERO_ADDRESS
    assert easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), voting)
    assert easy_track.hasRole(easy_track.PAUSE_ROLE(), voting)
    assert easy_track.hasRole(easy_track.UNPAUSE_ROLE(), voting)
    assert easy_track.hasRole(easy_track.CANCEL_ROLE(), voting)


def test_upgrade_to_called_by_stranger(stranger, easy_track):
    with reverts(
        "AccessControl: account 0x807c47a89f720fe4ee9b8343c286fc886f43191b is missing role 0x0000000000000000000000000000000000000000000000000000000000000000"
    ):
        easy_track.upgradeToAndCall(ZERO_ADDRESS, "", {"from": stranger})


def test_upgrade_to(owner, voting, easy_track):
    new_logic = owner.deploy(EasyTrack)
    easy_track.upgradeTo(new_logic, {"from": voting})
    proxy = Contract.from_abi("Proxy", easy_track, ContractProxy.abi)
    assert proxy.implementation() == new_logic


def test_create_motion_evm_script_factory_not_found(owner, stranger, easy_track):
    with reverts("EVM_SCRIPT_FACTORY_NOT_FOUND"):
        easy_track.createMotion(stranger, b"", {"from": owner})


def test_create_motion_has_no_permissions(
    voting, stranger, easy_track, evm_script_factory_stub
):
    permissions = stranger.address + "aabbccdd"
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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

    with reverts("HAS_NO_PERMISSIONS"):
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})


def test_create_motion_motions_limit_reached(
    voting, stranger, easy_track, evm_script_factory_stub
):
    easy_track.setMotionsCountLimit(1, {"from": voting})
    assert easy_track.motionsCountLimit() == 1

    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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
    assert len(easy_track.getMotions()) == 0
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})
    assert len(easy_track.getMotions()) == 1
    with reverts("MOTIONS_LIMIT_REACHED"):
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})


def test_create_motion(
    owner, voting, easy_track, evm_script_factory_stub, node_operators_registry_stub
):
    "Must create new motion with correct data and emit"
    "MotionCreated event when called by easy track"

    chain = Chain()

    # add easy track factory to create motions
    permissions = (
        node_operators_registry_stub.address
        + node_operators_registry_stub.setNodeOperatorStakingLimit.signature[2:]
        + node_operators_registry_stub.address[2:]
        + node_operators_registry_stub.getNodeOperator.signature[2:]
    )

    evm_script_calls = [
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                1, 200
            ),
        ),
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.getNodeOperator.encode_input(1, False),
        ),
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.setRewardAddress.encode_input(accounts[1]),
        ),
    ]
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
    assert easy_track.isEVMScriptFactory(evm_script_factory_stub)

    assert len(easy_track.getMotions()) == 0
    call_data = "0xaabbccddeeff"

    # test different combinations of permissions check
    # 1. Take first permission from list
    evm_script_factory_stub.setEVMScript(encode_call_script([evm_script_calls[0]]))
    easy_track.createMotion(evm_script_factory_stub, call_data, {"from": owner})

    # 2. Take second permission from list
    evm_script_factory_stub.setEVMScript(encode_call_script([evm_script_calls[1]]))
    easy_track.createMotion(evm_script_factory_stub, call_data, {"from": owner})

    # 3. has no permissions to run one of evm scripts
    evm_script_factory_stub.setEVMScript(
        encode_call_script(
            [evm_script_calls[1], evm_script_calls[0], evm_script_calls[2]]
        )
    )
    with reverts("HAS_NO_PERMISSIONS"):
        easy_track.createMotion(evm_script_factory_stub, call_data, {"from": owner})

    # 4. Take both permissions from the list in reverse order
    evm_script = encode_call_script([evm_script_calls[1], evm_script_calls[0]])
    evm_script_factory_stub.setEVMScript(evm_script)
    tx = easy_track.createMotion(evm_script_factory_stub, call_data, {"from": owner})

    assert len(tx.events) == 1
    assert tx.events["MotionCreated"]["_motionId"] == 3
    assert tx.events["MotionCreated"]["_creator"] == owner
    assert tx.events["MotionCreated"]["_evmScriptFactory"] == evm_script_factory_stub
    assert tx.events["MotionCreated"]["_evmScriptCallData"] == call_data
    assert tx.events["MotionCreated"]["_evmScript"] == evm_script

    motions = easy_track.getMotions()
    assert len(motions) == 3
    new_motion = motions[-1]

    assert new_motion[0] == 3  # id
    assert new_motion[1] == evm_script_factory_stub  # evmScriptFactory
    assert new_motion[2] == owner  # creator
    assert new_motion[3] == constants.MIN_MOTION_DURATION  # duration
    assert new_motion[4] == chain[-1].timestamp  # startDate
    assert new_motion[5] == chain[-1].number  # snapshotBlock
    assert (
        new_motion[6] == constants.DEFAULT_OBJECTIONS_THRESHOLD
    )  # objectionsThreshold
    assert new_motion[7] == 0  # objectionsAmount
    assert new_motion[8] == 0  # objectionsAmountPct
    assert new_motion[9] == web3.keccak(hexstr=evm_script).hex()  # evmScriptHash


def test_cancel_motion_not_found(owner, easy_track):
    with reverts("MOTION_NOT_FOUND"):
        easy_track.cancelMotion(1, {"from": owner})


def test_cancel_motion_not_owner(
    owner, voting, stranger, easy_track, evm_script_factory_stub
):
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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
    assert len(easy_track.getMotions()) == 0
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    assert len(easy_track.getMotions()) == 1
    with reverts("NOT_CREATOR"):
        easy_track.cancelMotion(1, {"from": stranger})


def test_cancel_motion(voting, stranger, easy_track, evm_script_factory_stub):
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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
    assert len(easy_track.getMotions()) == 0
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": stranger})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = easy_track.cancelMotion(motions[0][0], {"from": stranger})
    assert len(easy_track.getMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionCanceled"]["_motionId"] == motions[0][0]


def test_enact_motion_motion_not_found(owner, easy_track):
    with reverts("MOTION_NOT_FOUND"):
        easy_track.enactMotion(1, b"", {"from": owner})


def test_enact_motion_motion_not_passed(
    owner, voting, easy_track, evm_script_factory_stub
):
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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
    assert len(easy_track.getMotions()) == 0
    tx = easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    with reverts("MOTION_NOT_PASSED"):
        easy_track.enactMotion(
            motions[0][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": owner},
        )


def test_enact_motion_unexpected_evm_script(
    owner, voting, easy_track, evm_script_factory_stub
):
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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
    assert len(easy_track.getMotions()) == 0
    tx = easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain = Chain()
    chain.sleep(constants.MIN_MOTION_DURATION + 1)

    # replace evm script with different params
    # to change evm script hash
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


def test_enact_motion(
    owner, voting, easy_track, evm_script_factory_stub, evm_script_executor_stub
):
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
    evm_script = encode_call_script(
        [
            (
                evm_script_factory_stub.address,
                evm_script_factory_stub.setEVMScript.encode_input(b""),
            )
        ]
    )
    evm_script_factory_stub.setEVMScript(evm_script)
    assert len(easy_track.getMotions()) == 0
    tx = easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain = Chain()
    chain.sleep(constants.MIN_MOTION_DURATION + 1)

    assert evm_script_executor_stub.evmScript() == "0x"
    tx = easy_track.enactMotion(
        motions[0][0], tx.events["MotionCreated"]["_evmScriptCallData"], {"from": owner}
    )
    assert len(easy_track.getMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionEnacted"]["_motionId"] == motions[0][0]

    # validate that was passed correct evm script
    assert evm_script_executor_stub.evmScript() == evm_script


def test_object_to_motion_motion_not_found(owner, easy_track):
    with reverts("MOTION_NOT_FOUND"):
        easy_track.objectToMotion(1, {"from": owner})


def test_object_to_motion_multiple_times(
    owner, voting, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must fail with error: 'ALREADY_OBJECTED'"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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

    # send objection multiple times
    easy_track.objectToMotion(1, {"from": ldo_holders[0]})
    with reverts("ALREADY_OBJECTED"):
        easy_track.objectToMotion(1, {"from": ldo_holders[0]})


def test_object_to_motion_not_ldo_holder(
    owner, voting, stranger, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must fail with error: 'NOT_ENOUGH_BALANCE'"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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

    # send objection from user without ldo
    assert ldo_token.balanceOf(stranger) == 0
    with reverts("NOT_ENOUGH_BALANCE"):
        easy_track.objectToMotion(1, {"from": stranger})


def test_object_to_motion_by_tokens_holder(
    owner, voting, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must increase motion objections on correct amount and emit ObjectionSent event"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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

    # send objection from ldo holder
    tx = easy_track.objectToMotion(1, {"from": ldo_holders[0]})

    total_supply = ldo_token.totalSupply()
    holder_balance = ldo_token.balanceOf(ldo_holders[0])
    holder_part = 10000 * holder_balance / total_supply

    motion = easy_track.motions(0)

    assert motion[7] == ldo_token.balanceOf(ldo_holders[0])  # objectionsAmount
    assert motion[8] == holder_part  # objectionsAmountPct

    # validate events
    assert len(tx.events) == 1
    assert tx.events["MotionObjected"]["_motionId"] == motion[0]
    assert tx.events["MotionObjected"]["_objector"] == ldo_holders[0]
    assert tx.events["MotionObjected"]["_weight"] == holder_balance
    assert tx.events["MotionObjected"]["_votingPower"] == total_supply


def test_object_to_motion_rejected(
    owner, voting, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must delete motion and emit ObjectionSent and MotionRejected events"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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

    # send objections to pass threshold
    easy_track.objectToMotion(1, {"from": ldo_holders[0]})  # 0.2 % objections
    easy_track.objectToMotion(1, {"from": ldo_holders[1]})  # 0.4 % objections
    assert len(easy_track.getMotions()) == 1
    tx = easy_track.objectToMotion(1, {"from": ldo_holders[2]})  # 0.6 % objections
    assert len(easy_track.getMotions()) == 0

    # validate that events was emitted
    assert len(tx.events) == 2
    assert tx.events["MotionObjected"]["_motionId"] == 1
    assert tx.events["MotionObjected"]["_objector"] == ldo_holders[2]
    assert tx.events["MotionObjected"]["_weight"] == ldo_token.balanceOf(ldo_holders[2])
    assert tx.events["MotionObjected"]["_votingPower"] == ldo_token.totalSupply()
    assert tx.events["MotionRejected"]["_motionId"] == 1


def test_cancel_motions_in_random_order(
    owner, voting, easy_track, evm_script_factory_stub
):
    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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


def test_cancel_motions_called_by_stranger(stranger, easy_track):
    with reverts(access_controll_revert_message(stranger, CANCEL_ROLE)):
        easy_track.cancelMotions([], {"from": stranger})


def test_cancel_motions(
    owner,
    voting,
    stranger,
    easy_track,
    evm_script_factory_stub,
    finance,
    node_operators_registry_stub,
):
    "Must cancel all motions in the list. Emits MotionCanceled(_motionId) event for each canceled motion."
    "If motion with passed id doesn't exists skip it and doesn't emit event"

    # add evm script factory to easy track
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

    # cancel motions
    tx = easy_track.cancelMotions(motion_ids_to_cancel, {"from": voting})

    motions = easy_track.getMotions()
    assert len(motions) == 2
    assert motions[0][0] == 4
    assert motions[1][0] == 2

    assert len(tx.events["MotionCanceled"]) == 3
    for idx, motion_id in enumerate(motion_ids_to_cancel):
        assert tx.events["MotionCanceled"][idx]["_motionId"] == motion_id


def test_cancel_all_motions_called_by_stranger(stranger, easy_track):
    "Must fail with correct error message"
    with reverts(access_controll_revert_message(stranger, CANCEL_ROLE)):
        easy_track.cancelAllMotions({"from": stranger})


def test_cancel_all_motions(owner, voting, easy_track, evm_script_factory_stub):
    "Must cancel all active motions. Emits MotionCanceled(_motionId) event for each canceled motion"

    # add evm script factory to easy track
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


def test_set_evm_script_executor_called_by_stranger(stranger, easy_track):
    with reverts(access_controll_revert_message(stranger)):
        easy_track.setEVMScriptExecutor(ZERO_ADDRESS, {"from": stranger})


def test_set_evm_script_executor_called_by_owner(
    owner, voting, ldo_token, evm_script_executor
):
    logic = owner.deploy(EasyTrack)
    proxy = owner.deploy(
        ContractProxy,
        logic,
        logic.__EasyTrackStorage_init.encode_input(ldo_token, voting),
    )
    assert proxy.implementation() == logic
    easy_track = Contract.from_abi("EasyTrackProxied", proxy, EasyTrack.abi)

    assert easy_track.evmScriptExecutor() == ZERO_ADDRESS
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": voting})
    assert easy_track.evmScriptExecutor() == evm_script_executor


def test_pause_called_without_permissions(stranger, easy_track):
    assert not easy_track.paused()
    with reverts(access_controll_revert_message(stranger, PAUSE_ROLE)):
        easy_track.pause({"from": stranger})
    assert not easy_track.paused()


def test_pause_called_with_permissions(voting, easy_track):
    assert not easy_track.paused()
    easy_track.pause({"from": voting})
    assert easy_track.paused()


def test_can_object_to_motion(
    owner, voting, stranger, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must return False if caller has no governance tokens or if he has already voted."
    "Returns True in other cases"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": voting}
    )
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


def access_controll_revert_message(sender, role=DEFAULT_ADMIN_ROLE):
    PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"
    return PERMISSION_ERROR_TEMPLATE % (sender.address.lower(), role)
