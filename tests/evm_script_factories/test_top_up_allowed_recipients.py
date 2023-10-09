from datetime import datetime

from brownie.network import chain
from brownie import accounts, reverts, ZERO_ADDRESS

from utils.evm_script import encode_calldata, encode_call_script


def make_call_data(token, recipients, amounts):
    return encode_calldata("(address,address[],uint256[])", [token, recipients, amounts])


def test_top_up_factory_initial_state(
    allowed_recipients_registry,
    allowed_tokens_registry,
    accounts,
    finance,
    easy_track,
    TopUpAllowedRecipients,
):
    (recipients_registry, owner, _, _, _, _) = allowed_recipients_registry
    (tokens_registry, _, _, _) = allowed_tokens_registry

    trusted_caller = accounts[4]

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients,
        trusted_caller,
        recipients_registry,
        tokens_registry,
        finance,
        easy_track,
    )

    assert top_up_factory.allowedRecipientsRegistry() == recipients_registry
    assert top_up_factory.allowedTokensRegistry() == tokens_registry
    assert top_up_factory.trustedCaller() == trusted_caller
    assert top_up_factory.easyTrack() == easy_track
    assert top_up_factory.finance() == finance


def test_fail_if_zero_trusted_caller(
    allowed_recipients_registry,
    allowed_tokens_registry,
    finance,
    easy_track,
    TopUpAllowedRecipients,
):
    (registry, owner, _, _, _, _) = allowed_recipients_registry
    (tokens_registry, _, _, _) = allowed_tokens_registry

    with reverts("TRUSTED_CALLER_IS_ZERO_ADDRESS"):
        owner.deploy(
            TopUpAllowedRecipients, ZERO_ADDRESS, registry, tokens_registry, finance, easy_track
        )


def test_top_up_factory_constructor_zero_argument_addresses_allowed(
    TopUpAllowedRecipients, owner
):
    """Check no revert"""
    trusted_caller = accounts[4]
    owner.deploy(
        TopUpAllowedRecipients,
        trusted_caller,
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        ZERO_ADDRESS,
    )


def test_fail_create_evm_script_if_not_trusted_caller(
    top_up_allowed_recipients, stranger
):
    with reverts("CALLER_IS_FORBIDDEN"):
        top_up_allowed_recipients.createEVMScript(stranger, make_call_data(ZERO_ADDRESS, [], []))


def test_create_evm_script_is_permissionless(
    allowed_recipients_registry, allowed_tokens_registry, stranger, top_up_allowed_recipients, ldo
):
    (
        registry,
        _,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (token_registry, _, add_token_role_holder, _) = allowed_tokens_registry
    token_registry.addToken(ldo, {"from": add_token_role_holder})
    registry.addRecipient(
        stranger.address, "Test Recipient", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})
    call_data = make_call_data(ldo.address, [stranger.address], [123])
    trusted_caller = top_up_allowed_recipients.trustedCaller()
    top_up_allowed_recipients.createEVMScript(
        trusted_caller, call_data, {"from": stranger}
    )


def test_decode_evm_script_calldata_is_permissionless(
    stranger, top_up_allowed_recipients, ldo
):
    call_data = make_call_data(ldo.address, [stranger.address], [123])
    top_up_allowed_recipients.decodeEVMScriptCallData(call_data, {"from": stranger})


def test_fail_create_evm_script_if_length_mismatch(top_up_allowed_recipients, accounts, ldo):
    factory = top_up_allowed_recipients
    trusted_caller = top_up_allowed_recipients.trustedCaller()
    recipient = accounts[2].address

    with reverts("LENGTH_MISMATCH"):
        factory.createEVMScript(trusted_caller, make_call_data(ldo.address, [recipient], []))

    with reverts("LENGTH_MISMATCH"):
        factory.createEVMScript(trusted_caller, make_call_data(ldo.address, [], [123]))


def test_fail_create_evm_script_if_empty_data(top_up_allowed_recipients):
    factory = top_up_allowed_recipients
    trusted_caller = top_up_allowed_recipients.trustedCaller()

    with reverts("EMPTY_DATA"):
        factory.createEVMScript(trusted_caller, make_call_data(ZERO_ADDRESS, [], []))


def test_fail_create_evm_script_if_zero_amount(
    allowed_recipients_registry,
    allowed_tokens_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
):
    trusted_caller = owner
    recipient = accounts[4].address

    (
        registry,
        owner,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (tokens_registry, _, add_token_role_holder, _) = allowed_tokens_registry
    

    registry.addRecipient(
        recipient, "Test Recipient", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, tokens_registry, finance, easy_track
    )

    tokens_registry.addToken(ldo, {"from": add_token_role_holder})

    with reverts("ZERO_AMOUNT"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data(ldo.address, [recipient], [0]))

    with reverts("ZERO_AMOUNT"):
        top_up_factory.createEVMScript(
            trusted_caller, make_call_data(ldo.address, [recipient, recipient], [123, 0])
        )


def test_fail_create_evm_script_if_recipient_not_allowed(
    allowed_recipients_registry,
    allowed_tokens_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
    stranger,
):
    trusted_caller = owner
    recipient = accounts[4].address

    (
        registry,
        owner,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (tokens_registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addRecipient(
        recipient, "Test Recipient", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, tokens_registry, finance, easy_track
    )

    tokens_registry.addToken(ldo, {"from": add_token_role_holder})

    with reverts("RECIPIENT_NOT_ALLOWED"):
        top_up_factory.createEVMScript(
            trusted_caller, make_call_data(ldo.address, [stranger.address], [123])
        )


def test_fail_create_evm_script_if_token_not_allowed(
    allowed_recipients_registry,
    allowed_tokens_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
):
    trusted_caller = owner
    recipient = accounts[4].address

    (
        registry,
        owner,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (tokens_registry, _, _, _) = allowed_tokens_registry

    registry.addRecipient(
        recipient, "Test Recipient", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, tokens_registry, finance, easy_track
    )

    with reverts("TOKEN_NOT_ALLOWED"):
        top_up_factory.createEVMScript(
            trusted_caller, make_call_data(ldo.address, [recipient], [123])
        )


def test_top_up_factory_evm_script_creation_happy_path(
    allowed_recipients_registry,
    allowed_tokens_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
):
    trusted_caller = owner
    recipient = accounts[4].address

    (
        registry,
        owner,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (tokens_registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addRecipient(
        recipient, "Test Recipient", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, tokens_registry, finance, easy_track
    )

    tokens_registry.addToken(ldo, {"from": add_token_role_holder})

    payout = int(1e18)
    call_data = make_call_data(ldo.address, [recipient], [payout])
    evm_script = top_up_factory.createEVMScript(trusted_caller, call_data)
    assert top_up_factory.decodeEVMScriptCallData(call_data) == (ldo.address, [recipient], [payout])
    assert "Easy Track: top up recipient".encode("utf-8").hex() in str(evm_script)


def test_top_up_factory_evm_script_creation_multiple_recipients_happy_path(
    allowed_recipients_registry,
    allowed_tokens_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
):
    trusted_caller = owner
    recipients = [accounts[4].address, accounts[5].address]

    (
        registry,
        owner,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (tokens_registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addRecipient(
        recipients[0], "Test Recipient 1", {"from": add_recipient_role_holder}
    )
    registry.addRecipient(
        recipients[1], "Test Recipient 2", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, tokens_registry, finance, easy_track
    )

    tokens_registry.addToken(ldo, {"from": add_token_role_holder})

    payouts = [int(1e18), int(2e18)]
    call_data = make_call_data(ldo.address, recipients, payouts)
    evm_script = top_up_factory.createEVMScript(trusted_caller, call_data)
    assert top_up_factory.decodeEVMScriptCallData(call_data) == (ldo.address, recipients, payouts)
    assert "Easy Track: top up recipient".encode("utf-8").hex() in str(evm_script)


def test_fail_create_evm_script_if_sum_exceeds_limit(
    allowed_recipients_registry,
    allowed_tokens_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
):
    recipients = [accounts[4].address, accounts[5].address]
    payouts = [int(10e18), int(20e18)]
    call_data = make_call_data(ldo.address, recipients, payouts)

    (
        registry,
        owner,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (tokens_registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addRecipient(
        recipients[0], "Test Recipient 1", {"from": add_recipient_role_holder}
    )
    registry.addRecipient(
        recipients[1], "Test Recipient 2", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(20e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, owner, registry, tokens_registry, finance, easy_track
    )

    tokens_registry.addToken(ldo, {"from": add_token_role_holder})

    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        top_up_factory.createEVMScript(owner, call_data)


def test_create_evm_script_correctly(
    allowed_recipients_registry,
    allowed_tokens_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
):
    recipients = [accounts[4].address, accounts[5].address]
    payouts = [int(1e18), int(2e18)]
    totalAmount = int(3e18)

    (
        registry,
        owner,
        add_recipient_role_holder,
        _,
        set_limit_role_holder,
        _,
    ) = allowed_recipients_registry
    (tokens_registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addRecipient(
        recipients[0], "Test Recipient 1", {"from": add_recipient_role_holder}
    )
    registry.addRecipient(
        recipients[1], "Test Recipient 2", {"from": add_recipient_role_holder}
    )
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, owner, registry, tokens_registry, finance, easy_track
    )

    tokens_registry.addToken(ldo, {"from": add_token_role_holder})

    call_data = make_call_data(ldo.address, recipients, payouts)
    evm_script = top_up_factory.createEVMScript(owner, call_data)
    expected_evm_script = encode_call_script(
        [
            (
                registry.address,
                registry.updateSpentAmount.encode_input(totalAmount),
            ),
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    ldo, recipients[0], payouts[0], "Easy Track: top up recipient"
                ),
            ),
            (
                finance.address,
                finance.newImmediatePayment.encode_input(
                    ldo, recipients[1], payouts[1], "Easy Track: top up recipient"
                ),
            ),
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(top_up_allowed_recipients, ldo, accounts):
    recipient = accounts[4].address
    payout = int(1e18)
    call_data = make_call_data(ldo.address, [recipient], [payout])

    assert top_up_allowed_recipients.decodeEVMScriptCallData(call_data) == [
        ldo.address,
        [recipient],
        [payout],
    ]
