import pytest

from brownie import reverts
from brownie.network import chain
from dataclasses import dataclass

from utils import deployment, evm_script, test_helpers

MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60


@dataclass
class Recipient:
    address: str
    title: str


####
# FIXTURES
####


@pytest.fixture(scope="module")
def recipients(accounts):
    return [
        Recipient(address=accounts[7].address, title="recipient#1"),
        Recipient(address=accounts[8].address, title="recipient#2"),
        Recipient(address=accounts[9].address, title="recipient#3"),
    ]


@pytest.fixture(scope="module")
def add_allowed_recipient_by_motion(
    easy_track,
    allowed_recipients_registry,
    add_allowed_recipient_evm_script_factory,
    stranger,
):
    def _add_allowed_recipient_via_motion(recipient: Recipient):
        tx = easy_track.createMotion(
            add_allowed_recipient_evm_script_factory,
            evm_script.encode_calldata(
                "(address,string)", [recipient.address, recipient.title]
            ),
            {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
        )

        chain.sleep(easy_track.motionDuration() + 100)

        easy_track.enactMotion(
            tx.events["MotionCreated"]["_motionId"],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

        assert allowed_recipients_registry.isRecipientAllowed(recipient.address)

    return _add_allowed_recipient_via_motion


@pytest.fixture(scope="module")
def remove_allowed_recipient_by_motion(
    easy_track,
    allowed_recipients_registry,
    remove_allowed_recipient_evm_script_factory,
    stranger,
):
    def _remove_recipient_by_motion(recipient: Recipient):
        call_data = evm_script.encode_calldata("(address)", [recipient.address])

        tx = easy_track.createMotion(
            remove_allowed_recipient_evm_script_factory,
            call_data,
            {"from": remove_allowed_recipient_evm_script_factory.trustedCaller()},
        )

        chain.sleep(easy_track.motionDuration() + 100)

        easy_track.enactMotion(
            tx.events["MotionCreated"]["_motionId"],
            call_data,
            {"from": stranger},
        )
        assert not allowed_recipients_registry.isRecipientAllowed(recipient.address)

    return _remove_recipient_by_motion


@pytest.fixture(scope="module")
def create_top_up_allowed_recipients_motion(
    easy_track, top_up_allowed_recipients_evm_script_factory
):
    def _create_top_up_allowed_recipients_motion(recipients, top_up_amounts):
        recipient_addresses = [recipient.address for recipient in recipients]
        return easy_track.createMotion(
            top_up_allowed_recipients_evm_script_factory,
            evm_script.encode_calldata(
                "(address[],uint256[])", [recipient_addresses, top_up_amounts]
            ),
            {"from": top_up_allowed_recipients_evm_script_factory.trustedCaller()},
        )

    return _create_top_up_allowed_recipients_motion


@pytest.fixture(scope="module")
def top_up_allowed_recipient_by_motion(
    easy_track, create_top_up_allowed_recipients_motion, enact_motion_by_creation_tx
):
    def _top_up_allowed_recipient_by_motion(recipients, top_up_amounts):
        motion_creation_tx = create_top_up_allowed_recipients_motion(
            recipients, top_up_amounts
        )

        chain.sleep(easy_track.motionDuration() + 100)

        return enact_motion_by_creation_tx(motion_creation_tx)

    return _top_up_allowed_recipient_by_motion


@pytest.fixture(scope="module")
def get_balances(interface):
    def _get_balances(token, recipients):
        return [interface.ERC20(token).balanceOf(r.address) for r in recipients]

    return _get_balances


@pytest.fixture(scope="module")
def check_top_up_motion_enactment(
    allowed_recipients_registry,
    get_balances,
    top_up_allowed_recipients_evm_script_factory,
):
    def _check_top_up_motion_enactment(
        top_up_motion_enactment_tx, balances_before, top_up_recipients, top_up_amounts
    ):
        limit, duration = allowed_recipients_registry.getLimitParameters()

        spending = sum(top_up_amounts)
        spendable = limit - spending

        assert allowed_recipients_registry.isUnderSpendableBalance(spendable, 0)
        assert allowed_recipients_registry.isUnderSpendableBalance(
            limit, duration * MAX_SECONDS_IN_MONTH
        )
        assert (
            allowed_recipients_registry.getPeriodState()["_alreadySpentAmount"]
            == spending
        )
        assert (
            allowed_recipients_registry.getPeriodState()["_spendableBalanceInPeriod"]
            == spendable
        )

        balances = get_balances(
            top_up_allowed_recipients_evm_script_factory.token(),
            top_up_recipients,
        )
        for before, now, payment in zip(balances_before, balances, top_up_amounts):
            assert now == before + payment

        assert "SpendableAmountChanged" in top_up_motion_enactment_tx.events
        assert (
            top_up_motion_enactment_tx.events["SpendableAmountChanged"][
                "_alreadySpentAmount"
            ]
            == spending
        )
        assert (
            top_up_motion_enactment_tx.events["SpendableAmountChanged"][
                "_spendableBalance"
            ]
            == spendable
        )

    return _check_top_up_motion_enactment


@pytest.fixture(scope="module")
def enact_motion_by_creation_tx(easy_track, stranger):
    def _enact_motion_by_creation_tx(creation_tx):
        motion_id = creation_tx.events["MotionCreated"]["_motionId"]
        motion_calldata = creation_tx.events["MotionCreated"]["_evmScriptCallData"]

        return easy_track.enactMotion(motion_id, motion_calldata, {"from": stranger})

    return _enact_motion_by_creation_tx


####
# TESTS
####


def test_add_recipient_motion(
    easy_track,
    allowed_recipients_registry,
    add_allowed_recipient_evm_script_factory,
    recipients,
    stranger,
):
    recipient = recipients[0]

    call_data = evm_script.encode_calldata(
        "(address,string)", [recipient.address, recipient.title]
    )
    assert add_allowed_recipient_evm_script_factory.decodeEVMScriptCallData(
        call_data
    ) == [
        recipient.address,
        recipient.title,
    ]

    tx = easy_track.createMotion(
        add_allowed_recipient_evm_script_factory,
        call_data,
        {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
    )

    chain.sleep(easy_track.motionDuration() + 100)

    tx = easy_track.enactMotion(
        tx.events["MotionCreated"]["_motionId"],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    test_helpers.assert_event_exists(
        tx,
        "RecipientAdded",
        {"_recipient": recipient.address, "_title": recipient.title},
    )
    assert allowed_recipients_registry.isRecipientAllowed(recipient.address)
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 1


def test_add_multiple_recipients_by_concurrent_motions(
    easy_track,
    allowed_recipients_registry,
    add_allowed_recipient_evm_script_factory,
    recipients,
    stranger,
):
    recipient1, recipient2 = recipients[:2]

    tx = easy_track.createMotion(
        add_allowed_recipient_evm_script_factory,
        evm_script.encode_calldata(
            "(address,string)", [recipient1.address, recipient1.title]
        ),
        {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
    )
    motion1_id = tx.events["MotionCreated"]["_motionId"]
    motion1_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    tx = easy_track.createMotion(
        add_allowed_recipient_evm_script_factory,
        evm_script.encode_calldata(
            "(address,string)", [recipient2.address, recipient2.title]
        ),
        {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
    )
    motion2_id = tx.events["MotionCreated"]["_motionId"]
    motion2_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    chain.sleep(easy_track.motionDuration() + 100)

    easy_track.enactMotion(motion2_id, motion2_calldata, {"from": stranger})
    easy_track.enactMotion(motion1_id, motion1_calldata, {"from": stranger})

    assert allowed_recipients_registry.isRecipientAllowed(recipient1.address)
    assert allowed_recipients_registry.isRecipientAllowed(recipient2.address)
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 2


def test_fail_add_same_recipient_by_second_concurrent_motion(
    easy_track,
    add_allowed_recipient_evm_script_factory,
    recipients,
    stranger,
):
    recipient = recipients[0]

    tx = easy_track.createMotion(
        add_allowed_recipient_evm_script_factory,
        evm_script.encode_calldata(
            "(address,string)", [recipient.address, recipient.title]
        ),
        {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
    )
    motion1_id = tx.events["MotionCreated"]["_motionId"]
    motion1_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    tx = easy_track.createMotion(
        add_allowed_recipient_evm_script_factory,
        evm_script.encode_calldata(
            "(address,string)", [recipient.address, recipient.title]
        ),
        {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
    )
    motion2_id = tx.events["MotionCreated"]["_motionId"]
    motion2_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    chain.sleep(easy_track.motionDuration() + 100)

    easy_track.enactMotion(motion1_id, motion1_calldata, {"from": stranger})

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        easy_track.enactMotion(motion2_id, motion2_calldata, {"from": stranger})


def test_fail_if_add_same_recipient_twice(recipients, add_allowed_recipient_by_motion):
    add_allowed_recipient_by_motion(recipients[0])

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        add_allowed_recipient_by_motion(recipients[0])


def test_remove_recipient_motion(
    recipients,
    easy_track,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    enact_motion_by_creation_tx,
    remove_allowed_recipient_evm_script_factory,
):
    allowed_recipient = recipients[0]
    add_allowed_recipient_by_motion(allowed_recipient)

    tx = easy_track.createMotion(
        remove_allowed_recipient_evm_script_factory,
        evm_script.encode_calldata("(address)", [allowed_recipient.address]),
        {"from": remove_allowed_recipient_evm_script_factory.trustedCaller()},
    )

    chain.sleep(easy_track.motionDuration() + 100)

    motion_enactment_tx = enact_motion_by_creation_tx(creation_tx=tx)

    test_helpers.assert_event_exists(
        motion_enactment_tx,
        "RecipientRemoved",
        {"_recipient": allowed_recipient.address},
    )

    assert not allowed_recipients_registry.isRecipientAllowed(allowed_recipient.address)
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 0


def test_fail_remove_recipient_if_empty_allowed_recipients_list(
    recipients, allowed_recipients_registry, remove_allowed_recipient_by_motion
):
    assert len(allowed_recipients_registry.getAllowedRecipients()) == 0

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_allowed_recipient_by_motion(recipients[0])


def test_fail_remove_recipient_if_it_is_not_allowed(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    remove_allowed_recipient_by_motion,
):
    allowed_recipient, not_allowed_recipient = recipients[0], recipients[1]

    add_allowed_recipient_by_motion(allowed_recipient)

    assert len(allowed_recipients_registry.getAllowedRecipients()) > 0
    assert not allowed_recipients_registry.isRecipientAllowed(
        not_allowed_recipient.address
    )

    with reverts("ALLOWED_RECIPIENT_NOT_FOUND"):
        remove_allowed_recipient_by_motion(not_allowed_recipient)


def test_top_up_single_recipient(
    recipients,
    easy_track,
    allowed_recipients_limit_params,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipients_evm_script_factory,
    get_balances,
    check_top_up_motion_enactment,
    stranger,
):
    allowed_recipient = recipients[0]

    add_allowed_recipient_by_motion(allowed_recipient)

    top_up_recipient_addresses = [allowed_recipient.address]
    top_up_amounts = [2 * 10 ** 18]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    script_call_data = evm_script.encode_calldata(
        "(address[],uint256[])", [top_up_recipient_addresses, top_up_amounts]
    )

    tx = easy_track.createMotion(
        top_up_allowed_recipients_evm_script_factory,
        script_call_data,
        {"from": top_up_allowed_recipients_evm_script_factory.trustedCaller()},
    )
    motion_id = tx.events["MotionCreated"]["_motionId"]

    chain.sleep(easy_track.motionDuration() + 100)

    balances_before = get_balances(
        top_up_allowed_recipients_evm_script_factory.token(), [allowed_recipient]
    )
    tx = easy_track.enactMotion(motion_id, script_call_data, {"from": stranger})

    check_top_up_motion_enactment(
        top_up_motion_enactment_tx=tx,
        balances_before=balances_before,
        top_up_recipients=[allowed_recipient],
        top_up_amounts=top_up_amounts,
    )


def test_top_up_multiple_recipients(
    recipients,
    easy_track,
    get_balances,
    allowed_recipients_limit_params,
    enact_motion_by_creation_tx,
    check_top_up_motion_enactment,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    top_up_amounts = [2 * 10 ** 18, 1 * 10 ** 18]

    motion_creation_tx = easy_track.createMotion(
        top_up_allowed_recipients_evm_script_factory,
        evm_script.encode_calldata(
            "(address[],uint256[])",
            [
                [allowed_recipients[0].address, allowed_recipients[1].address],
                top_up_amounts,
            ],
        ),
        {"from": top_up_allowed_recipients_evm_script_factory.trustedCaller()},
    )

    chain.sleep(easy_track.motionDuration() + 100)

    balances_before = get_balances(
        token=top_up_allowed_recipients_evm_script_factory.token(),
        recipients=allowed_recipients,
    )

    motion_enactment_tx = enact_motion_by_creation_tx(creation_tx=motion_creation_tx)

    check_top_up_motion_enactment(
        top_up_motion_enactment_tx=motion_enactment_tx,
        balances_before=balances_before,
        top_up_recipients=allowed_recipients,
        top_up_amounts=top_up_amounts,
    )


def test_top_up_motion_enacted_in_next_period(
    recipients,
    get_balances,
    allowed_recipients_limit_params,
    check_top_up_motion_enactment,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    top_up_allowed_recipients_evm_script_factory,
    enact_motion_by_creation_tx,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    top_up_amounts = [int(3e18), int(90e18)]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, top_up_amounts
    )

    chain.sleep(allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    balances_before = get_balances(
        token=top_up_allowed_recipients_evm_script_factory.token(),
        recipients=allowed_recipients,
    )
    motion_enactment_tx = enact_motion_by_creation_tx(motion_creation_tx)

    check_top_up_motion_enactment(
        top_up_motion_enactment_tx=motion_enactment_tx,
        balances_before=balances_before,
        top_up_recipients=allowed_recipients,
        top_up_amounts=top_up_amounts,
    )


def test_top_up_motion_ended_and_enacted_in_next_period(
    recipients,
    easy_track,
    get_balances,
    allowed_recipients_limit_params,
    allowed_recipients_registry,
    enact_motion_by_creation_tx,
    check_top_up_motion_enactment,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    top_up_amounts = [int(3e18), int(90e18)]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )
    test_helpers.advance_chain_time_to_n_seconds_before_current_period_end(
        allowed_recipients_limit_params.duration, easy_track.motionDuration() // 2
    )

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, top_up_amounts
    )

    _, _, *old_period_range = allowed_recipients_registry.getPeriodState()

    chain.sleep(easy_track.motionDuration())

    balances_before = get_balances(
        token=top_up_allowed_recipients_evm_script_factory.token(),
        recipients=allowed_recipients,
    )

    motion_enactment_tx = enact_motion_by_creation_tx(motion_creation_tx)

    check_top_up_motion_enactment(
        top_up_motion_enactment_tx=motion_enactment_tx,
        balances_before=balances_before,
        top_up_recipients=allowed_recipients,
        top_up_amounts=top_up_amounts,
    )

    _, _, *new_period_range = allowed_recipients_registry.getPeriodState()
    assert (
        old_period_range != new_period_range
    ), "check periods when the motion was created and when it ended are different"


def test_top_up_motion_enacted_in_second_next_period(
    recipients,
    get_balances,
    allowed_recipients_limit_params,
    enact_motion_by_creation_tx,
    check_top_up_motion_enactment,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    top_up_allowed_recipients_evm_script_factory,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    top_up_amounts = [int(3e18), int(90e18)]

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, top_up_amounts
    )

    chain.sleep(2 * allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    balances_before = get_balances(
        token=top_up_allowed_recipients_evm_script_factory.token(),
        recipients=allowed_recipients,
    )

    motion_enactment_tx = enact_motion_by_creation_tx(motion_creation_tx)

    check_top_up_motion_enactment(
        top_up_motion_enactment_tx=motion_enactment_tx,
        balances_before=balances_before,
        top_up_recipients=allowed_recipients,
        top_up_amounts=top_up_amounts,
    )


def test_spendable_balance_is_renewed_in_next_period(
    recipients,
    easy_track,
    allowed_recipients_limit_params,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
    top_up_allowed_recipients_evm_script_factory,
):
    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    assert (
        allowed_recipients_registry.spendableBalance()
        == allowed_recipients_limit_params.limit
    )

    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    top_up_amounts = [int(10e18), int(90e18)]

    top_up_allowed_recipient_by_motion(allowed_recipients, top_up_amounts)

    amount_spent = sum(top_up_amounts)
    assert allowed_recipients_registry.getPeriodState()[0] == amount_spent
    assert (
        allowed_recipients_registry.spendableBalance()
        == allowed_recipients_limit_params.limit - amount_spent
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(allowed_recipients[:1], [1])

    chain.sleep(allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    # cannot just check the views `spendableBalance` and `getPeriodState`
    # because they are not updated without a call of updateSpentAmount
    # or setLimitParameters. So trying to make a full period limit amount payout
    top_up_allowed_recipient_by_motion(
        allowed_recipients[:1], [allowed_recipients_limit_params.limit]
    )

    assert (
        allowed_recipients_registry.getPeriodState()[0]
        == allowed_recipients_limit_params.limit
    )
    assert allowed_recipients_registry.spendableBalance() == 0


def test_fail_enact_top_up_motion_if_recipient_removed_by_other_motion(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    remove_allowed_recipient_by_motion,
    enact_motion_by_creation_tx,
):
    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    recipient_to_remove = allowed_recipients[0]
    top_up_amounts = [int(40e18), int(30e18)]

    motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, top_up_amounts
    )

    remove_allowed_recipient_by_motion(recipient_to_remove)

    with reverts("RECIPIENT_NOT_ALLOWED"):
        enact_motion_by_creation_tx(motion_creation_tx)


def test_fail_create_top_up_motion_if_exceeds_limit(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
):
    allowed_recipient = recipients[0]

    add_allowed_recipient_by_motion(allowed_recipient)

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        exceeded_top_up_amounts = [allowed_recipients_limit_params.limit + 1]
        create_top_up_allowed_recipients_motion(
            [allowed_recipient], exceeded_top_up_amounts
        )


def test_fail_to_create_top_up_motion_which_exceeds_spendable(
    recipients,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    top_up_allowed_recipient_by_motion,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    first_top_up_amounts = [int(40e18), int(60e18)]
    assert sum(first_top_up_amounts) == allowed_recipients_limit_params.limit

    top_up_allowed_recipient_by_motion(allowed_recipients, first_top_up_amounts)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        second_top_up_amounts = [1, 1]
        top_up_allowed_recipient_by_motion(allowed_recipients, second_top_up_amounts)


def test_fail_2nd_top_up_motion_enactment_due_limit_but_can_enact_in_next(
    recipients,
    easy_track,
    allowed_recipients_limit_params,
    enact_motion_by_creation_tx,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    first_top_up_amount = [int(40e18), int(30e18)]
    second_top_up_amount = [int(30e18), int(20e18)]
    assert (
        sum(first_top_up_amount + second_top_up_amount)
        > allowed_recipients_limit_params.limit
    )
    first_motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, first_top_up_amount
    )
    second_motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, second_top_up_amount
    )

    chain.sleep(easy_track.motionDuration() + 100)

    enact_motion_by_creation_tx(first_motion_creation_tx)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        enact_motion_by_creation_tx(second_motion_creation_tx)

    chain.sleep(allowed_recipients_limit_params.duration * MAX_SECONDS_IN_MONTH)

    enact_motion_by_creation_tx(second_motion_creation_tx)


def test_fail_2nd_top_up_motion_creation_in_period_if_it_exceeds_spendable(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    allowed_recipients_limit_params,
    top_up_allowed_recipient_by_motion,
):
    """Revert 2nd payout which together with 1st payout exceed the current period limit"""

    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    first_top_up_amounts = [int(3e18), int(90e18)]
    second_top_up_amounts = [int(5e18), int(4e18)]

    assert (
        sum(first_top_up_amounts + second_top_up_amounts)
        > allowed_recipients_limit_params.limit
    )

    top_up_allowed_recipient_by_motion(allowed_recipients, first_top_up_amounts)

    assert sum(second_top_up_amounts) > allowed_recipients_registry.spendableBalance()

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(allowed_recipients, second_top_up_amounts)


def test_fail_top_up_if_limit_decreased_while_motion_is_in_flight(
    recipients,
    easy_track,
    lido_contracts,
    allowed_recipients_registry,
    allowed_recipients_limit_params,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    enact_motion_by_creation_tx,
):
    allowed_recipients = recipients[:1]

    add_allowed_recipient_by_motion(allowed_recipients[0])

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    top_up_amounts = [allowed_recipients_limit_params.limit]
    motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, top_up_amounts
    )

    allowed_recipients_registry.setLimitParameters(
        allowed_recipients_limit_params.limit // 2,
        allowed_recipients_limit_params.duration,
        {"from": lido_contracts.aragon.agent},
    )

    chain.sleep(easy_track.motionDuration() + 100)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        enact_motion_by_creation_tx(motion_creation_tx)


def test_top_up_if_limit_increased_while_motion_is_in_flight(
    recipients,
    easy_track,
    get_balances,
    lido_contracts,
    allowed_recipients_limit_params,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    create_top_up_allowed_recipients_motion,
    enact_motion_by_creation_tx,
    top_up_allowed_recipients_evm_script_factory,
    check_top_up_motion_enactment,
):

    allowed_recipients = recipients[:1]
    add_allowed_recipient_by_motion(allowed_recipients[0])

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    top_up_amounts = [allowed_recipients_limit_params.limit]
    motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, top_up_amounts
    )

    allowed_recipients_registry.setLimitParameters(
        3 * allowed_recipients_limit_params.limit,
        allowed_recipients_limit_params.duration,
        {"from": lido_contracts.aragon.agent},
    )

    balances_before = get_balances(
        top_up_allowed_recipients_evm_script_factory.token(), allowed_recipients
    )

    chain.sleep(easy_track.motionDuration() + 100)

    motion_enactment_tx = enact_motion_by_creation_tx(motion_creation_tx)

    check_top_up_motion_enactment(
        motion_enactment_tx, balances_before, allowed_recipients, top_up_amounts
    )


def test_two_motion_seconds_failed_to_enact_due_limit_but_succeeded_after_limit_increased(
    recipients,
    easy_track,
    add_allowed_recipient_by_motion,
    allowed_recipients_limit_params,
    allowed_recipients_registry,
    create_top_up_allowed_recipients_motion,
    enact_motion_by_creation_tx,
    lido_contracts,
):
    allowed_recipients = recipients[:2]

    add_allowed_recipient_by_motion(allowed_recipients[0])
    add_allowed_recipient_by_motion(allowed_recipients[1])

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        allowed_recipients_limit_params.duration
    )

    first_top_up_amounts = [int(40e18), int(60e18)]
    assert sum(first_top_up_amounts) == allowed_recipients_limit_params.limit
    second_top_up_amounts = [1, 1]

    first_motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, first_top_up_amounts
    )

    second_motion_creation_tx = create_top_up_allowed_recipients_motion(
        allowed_recipients, second_top_up_amounts
    )

    chain.sleep(easy_track.motionDuration() + 100)

    enact_motion_by_creation_tx(first_motion_creation_tx)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        enact_motion_by_creation_tx(second_motion_creation_tx)

    allowed_recipients_registry.setLimitParameters(
        allowed_recipients_limit_params.limit + sum(second_top_up_amounts),
        allowed_recipients_limit_params.duration,
        {"from": lido_contracts.aragon.agent},
    )

    enact_motion_by_creation_tx(second_motion_creation_tx)


@pytest.mark.parametrize(
    "initial_period_duration,new_period_duration", [(3, 2), (3, 6), (12, 1), (1, 12)]
)
def test_top_up_spendable_renewal_if_period_duration_changed(
    recipients,
    allowed_recipients_registry,
    add_allowed_recipient_by_motion,
    lido_contracts,
    top_up_allowed_recipient_by_motion,
    initial_period_duration: int,
    new_period_duration: int,
):
    period_limit = 100 * 10 ** 18
    allowed_recipients = recipients[:1]

    add_allowed_recipient_by_motion(allowed_recipients[0])

    first_top_up_amount = [period_limit]
    second_top_up_amount = [1]  # just 1 wei

    allowed_recipients_registry.setLimitParameters(
        period_limit, initial_period_duration, {"from": lido_contracts.aragon.agent}
    )
    test_helpers.advance_chain_time_to_beginning_of_the_next_period(
        initial_period_duration
    )

    top_up_allowed_recipient_by_motion(allowed_recipients, first_top_up_amount)

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(allowed_recipients, second_top_up_amount)

    allowed_recipients_registry.setLimitParameters(
        period_limit, new_period_duration, {"from": lido_contracts.aragon.agent}
    )

    # expect it to revert because although calendar grid period has changed
    # the amount spent and the limit are left intact
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_allowed_recipient_by_motion(allowed_recipients, second_top_up_amount)

    test_helpers.advance_chain_time_to_beginning_of_the_next_period(new_period_duration)

    # when move time to time point in the next period of the new calendar period grid
    # expect the spendable get renewed
    top_up_allowed_recipient_by_motion(allowed_recipients, second_top_up_amount)
