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


def test_deploy(owner, ldo_token):
    logic = owner.deploy(EasyTrack)
    proxy = owner.deploy(
        ContractProxy, logic, logic.__EasyTrack_init.encode_input(ldo_token)
    )
    assert proxy.implementation() == logic
    easy_track = Contract.from_abi("EasyTrackProxied", proxy, EasyTrack.abi)

    assert easy_track.owner() == owner
    assert easy_track.governanceToken() == ldo_token
    assert easy_track.evmScriptExecutor() == ZERO_ADDRESS


def test_upgrade_to_called_by_stranger(stranger, easy_track):
    with reverts("Ownable: caller is not the owner"):
        easy_track.upgradeToAndCall(ZERO_ADDRESS, "", {"from": stranger})


def test_upgrade_to(owner, easy_track):
    new_logic = owner.deploy(EasyTrack)
    easy_track.upgradeTo(new_logic, {"from": owner})
    proxy = Contract.from_abi("Proxy", easy_track, ContractProxy.abi)
    assert proxy.implementation() == new_logic


def test_create_motion_evm_script_factory_not_found(owner, stranger, easy_track):
    with reverts("EVM_SCRIPT_FACTORY_NOT_FOUND"):
        easy_track.createMotion(stranger, b"", {"from": owner})


def test_create_motion_has_no_permissions(
    owner, stranger, easy_track, evm_script_factory_stub
):
    permissions = stranger.address + "aabbccdd"
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})


def test_create_motion_motions_limit_reached(
    owner, stranger, easy_track, evm_script_factory_stub
):
    easy_track.setMotionsCountLimit(1, {"from": owner})
    assert easy_track.motionsCountLimit() == 1

    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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
    with reverts("MOTIONS_LIMIT_REACHED"):
        easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})


def test_create_motion(
    owner, easy_track, evm_script_factory_stub, node_operators_registry_stub
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
        evm_script_factory_stub, permissions, {"from": owner}
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
    assert new_motion[10] == call_data  # evmScriptCallData


def test_cancel_motion_not_found(owner, easy_track):
    with reverts("MOTION_NOT_FOUND"):
        easy_track.cancelMotion(1, {"from": owner})


def test_cancel_motion_not_owner(owner, stranger, easy_track, evm_script_factory_stub):
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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


def test_cancel_motion(owner, easy_track, evm_script_factory_stub):
    easy_track.setMotionsCountLimit(1, {"from": owner})
    assert easy_track.motionsCountLimit() == 1

    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = easy_track.cancelMotion(motions[0][0], {"from": owner})
    assert len(easy_track.getMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionCanceled"]["_motionId"] == motions[0][0]


def test_enact_motion_motion_not_found(owner, easy_track):
    with reverts("MOTION_NOT_FOUND"):
        easy_track.enactMotion(1, {"from": owner})


def test_enact_motion_motion_not_passed(owner, easy_track, evm_script_factory_stub):
    easy_track.setMotionsCountLimit(1, {"from": owner})
    assert easy_track.motionsCountLimit() == 1

    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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
    motions = easy_track.getMotions()
    assert len(motions) == 1

    with reverts("MOTION_NOT_PASSED"):
        easy_track.enactMotion(motions[0][0], {"from": owner})


def test_enact_motion_unexpected_evm_script(owner, easy_track, evm_script_factory_stub):
    easy_track.setMotionsCountLimit(1, {"from": owner})
    assert easy_track.motionsCountLimit() == 1

    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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
        easy_track.enactMotion(motions[0][0], {"from": owner})


def test_enact_motion(
    owner, easy_track, evm_script_factory_stub, evm_script_executor_stub
):
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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
    easy_track.createMotion(evm_script_factory_stub, b"", {"from": owner})
    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain = Chain()
    chain.sleep(constants.MIN_MOTION_DURATION + 1)

    assert evm_script_executor_stub.evmScript() == "0x"
    tx = easy_track.enactMotion(motions[0][0], {"from": owner})
    assert len(easy_track.getMotions()) == 0
    assert len(tx.events) == 1
    assert tx.events["MotionEnacted"]["_motionId"] == motions[0][0]

    # validate that was passed correct evm script
    assert evm_script_executor_stub.evmScript() == evm_script


def test_object_to_motion_motion_not_found(owner, easy_track):
    with reverts("MOTION_NOT_FOUND"):
        easy_track.objectToMotion(1, {"from": owner})


def test_object_to_motion_multiple_times(
    owner, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must fail with error: 'ALREADY_OBJECTED'"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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
    owner, stranger, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must fail with error: 'NOT_ENOUGH_BALANCE'"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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


def test_send_objection_by_tokens_holder(
    owner, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must increase motion objections on correct amount and emit ObjectionSent event"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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


def test_send_objection_rejected(
    owner, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must delete motion and emit ObjectionSent and MotionRejected events"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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


def test_can_object_to_motion(
    owner, stranger, ldo_holders, ldo_token, easy_track, evm_script_factory_stub
):
    "Must return False if caller has no governance tokens or if he has already voted."
    "Returns True in other cases"

    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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


def test_cancel_motions_in_random_order(owner, easy_track, evm_script_factory_stub):
    # add evm script factory to easy track
    permissions = (
        evm_script_factory_stub.address
        + evm_script_factory_stub.setEVMScript.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        evm_script_factory_stub, permissions, {"from": owner}
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


def test_set_evm_script_executor_called_by_stranger(stranger, easy_track):
    with reverts("Ownable: caller is not the owner"):
        easy_track.setEvmScriptExecutor(ZERO_ADDRESS, {"from": stranger})


def test_set_evm_script_executor_called_by_owner(owner, ldo_token, evm_script_executor):
    logic = owner.deploy(EasyTrack)
    proxy = owner.deploy(
        ContractProxy, logic, logic.__EasyTrack_init.encode_input(ldo_token)
    )
    assert proxy.implementation() == logic
    easy_track = Contract.from_abi("EasyTrackProxied", proxy, EasyTrack.abi)

    assert easy_track.evmScriptExecutor() == ZERO_ADDRESS
    easy_track.setEvmScriptExecutor(evm_script_executor, {"from": owner})
    assert easy_track.evmScriptExecutor() == evm_script_executor
