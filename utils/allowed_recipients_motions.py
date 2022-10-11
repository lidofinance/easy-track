from brownie.network import chain
from typing import List

from eth_abi import encode_single
from utils.evm_script import encode_call_script, encode_calldata

from utils.config import get_network_name

from utils.lido import create_voting, execute_voting

from utils.test_helpers import (
    assert_event_exists,
)

import constants


MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60


def add_recipient_by_motion(recipient, recipient_title, easy_track, add_recipient_factory):
    tx = easy_track.createMotion(
        add_recipient_factory,
        encode_calldata("(address,string)", [recipient.address, recipient_title]),
        {"from": add_recipient_factory.trustedCaller()},
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": recipient},
    )


def remove_recipient_by_motion(
    recipient, easy_track, remove_recipient_factory, allowed_recipients_registry
):
    call_data = encode_single("(address)", [recipient.address])
    assert remove_recipient_factory.decodeEVMScriptCallData(call_data) == recipient.address

    tx = easy_track.createMotion(
        remove_recipient_factory,
        call_data,
        {"from": remove_recipient_factory.trustedCaller()},
    )

    assert tx.events["MotionCreated"]["_evmScriptCallData"] == "0x" + call_data.hex()

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    tx = easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        call_data,
        {"from": recipient},
    )
    assert_event_exists(
        tx,
        "RecipientRemoved",
        {"_recipient": recipient},
    )
    assert not allowed_recipients_registry.isRecipientAllowed(recipient)


def set_limit_parameters_by_aragon_voting(
    period_limit, period_duration, allowed_recipients_registry, agent
):
    """Do Aragon voting to set limit parameters to the allowed recipients registry"""
    set_limit_parameters_voting_id, _ = create_voting(
        evm_script=encode_call_script(
            [
                (
                    allowed_recipients_registry.address,
                    allowed_recipients_registry.setLimitParameters.encode_input(
                        period_limit,
                        period_duration,
                    ),
                ),
            ]
        ),
        description="Set limit parameters",
        network=get_network_name(),
        tx_params={"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    execute_voting(set_limit_parameters_voting_id, get_network_name())

    assert allowed_recipients_registry.getLimitParameters() == (period_limit, period_duration)


def create_top_up_motion(recipients: List[str], amounts: List[int], easy_track, top_up_factory):
    script_call_data = encode_single("(address[],uint256[])", [recipients, amounts])
    tx = easy_track.createMotion(
        top_up_factory,
        script_call_data,
        {"from": top_up_factory.trustedCaller()},
    )
    motion_id = tx.events["MotionCreated"]["_motionId"]
    return motion_id, script_call_data


def do_payout_to_allowed_recipients_by_motion(recipients, amounts, easy_track, top_up_factory):
    motion_id, script_call_data = create_top_up_motion(
        recipients, amounts, easy_track, top_up_factory
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    easy_track.enactMotion(
        motion_id,
        script_call_data,
        {"from": recipients[0]},
    )
