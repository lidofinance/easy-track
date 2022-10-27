from brownie.network import chain
from brownie import interface
from typing import List

from eth_abi import encode_single
from utils.evm_script import encode_call_script, encode_calldata

from utils.config import get_network_name

from utils.lido import create_voting, execute_voting

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
        tx.events["MotionCreated"]["_motionId"],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": recipient},
    )


def remove_recipient_by_motion(
    recipient, easy_track, remove_recipient_factory, allowed_recipients_registry
):
    call_data = encode_single("(address)", [recipient.address])

    tx = easy_track.createMotion(
        remove_recipient_factory,
        call_data,
        {"from": remove_recipient_factory.trustedCaller()},
    )

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    easy_track.enactMotion(
        tx.events["MotionCreated"]["_motionId"],
        call_data,
        {"from": recipient},
    )
    assert not allowed_recipients_registry.isRecipientAllowed(recipient)


def set_limit_parameters_by_aragon_voting(
    period_limit: int, period_duration: int, allowed_recipients_registry, agent
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


def get_balances(recipients, token):
    return [interface.ERC20(token).balanceOf(r) for r in recipients]


def check_top_up(
    tx, finance_balance_before, balances_before, recipients, payouts, registry, top_up_factory, agent
):
    limit, duration = registry.getLimitParameters()
    spending = sum(payouts)
    spendable = limit - spending

    assert registry.isUnderSpendableBalance(spendable, 0)
    assert registry.isUnderSpendableBalance(limit, duration * MAX_SECONDS_IN_MONTH)
    assert registry.getPeriodState()["_alreadySpentAmount"] == spending
    assert registry.getPeriodState()["_spendableBalanceInPeriod"] == spendable

    balances = get_balances(recipients, top_up_factory.token())
    for before, now, payment in zip(balances_before, balances, payouts):
        assert now == before + payment

    agent_balance = interface.ERC20(top_up_factory.token()).balanceOf(agent)
    assert finance_balance_before - spending == agent_balance

    assert "SpendableAmountChanged" in tx.events
    assert tx.events["SpendableAmountChanged"]["_alreadySpentAmount"] == spending
    assert tx.events["SpendableAmountChanged"]["_spendableBalance"] == spendable
