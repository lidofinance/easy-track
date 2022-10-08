from datetime import datetime

from brownie.network import chain
from brownie import accounts, reverts, ZERO_ADDRESS

from eth_abi import encode_single


def make_call_data(recipients, amounts):
    return encode_single("(address[],uint256[])", [recipients, amounts])


def test_top_up_factory_initial_state(
    allowed_recipients_registry,
    accounts,
    finance,
    ldo,
    easy_track,
    TopUpAllowedRecipients,
):
    (registry, owner, _, _, _, _) = allowed_recipients_registry

    trusted_caller = accounts[4]

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, finance, ldo, easy_track
    )

    assert top_up_factory.token() == ldo
    assert top_up_factory.allowedRecipientsRegistry() == registry
    assert top_up_factory.trustedCaller() == trusted_caller
    assert top_up_factory.easyTrack() == easy_track
    assert top_up_factory.finance() == finance


def test_fail_if_zero_trusted_caller(
    allowed_recipients_registry,
    finance,
    ldo,
    easy_track,
    TopUpAllowedRecipients,
):
    (registry, owner, _, _, _, _) = allowed_recipients_registry

    with reverts("TRUSTED_CALLER_IS_ZERO_ADDRESS"):
        owner.deploy(TopUpAllowedRecipients, ZERO_ADDRESS, registry, finance, ldo, easy_track)


def test_top_up_factory_constructor_zero_argument_addresses_allowed(TopUpAllowedRecipients, owner):
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


def test_top_up_factory_evm_script_creation_happy_path(
    allowed_recipients_registry,
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

    registry.addRecipient(recipient, "Test Recipient", {"from": add_recipient_role_holder})
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, finance, ldo, easy_track
    )

    payout = int(1e18)
    call_data = make_call_data([recipient], [payout])
    evm_script = top_up_factory.createEVMScript(trusted_caller, call_data)
    assert top_up_factory.decodeEVMScriptCallData(call_data) == ([recipient], [payout])
    assert "Top up allowed recipients".encode("utf-8").hex() in str(evm_script)


def test_fail_create_evm_script_if_params_invalid_according_to_registry(
    allowed_recipients_registry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
    stranger,
):
    """Fail if the parameters are incorrect according to the registry"""
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

    registry.addRecipient(recipient, "Test Recipient", {"from": add_recipient_role_holder})
    registry.setLimitParameters(int(100e18), 12, {"from": set_limit_role_holder})

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, finance, ldo, easy_track
    )

    with reverts("ZERO_AMOUNT"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data([recipient], [0]))

    with reverts("ZERO_AMOUNT"):
        top_up_factory.createEVMScript(
            trusted_caller, make_call_data([recipient, recipient], [123, 0])
        )

    with reverts("RECIPIENT_NOT_ALLOWED"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data([stranger.address], [123]))


def test_fail_create_evm_script_if_invalid_parameters_format(top_up_allowed_recipients, accounts):
    """Check the data format is invalid"""
    factory = top_up_allowed_recipients
    trusted_caller = top_up_allowed_recipients.trustedCaller()
    recipient = accounts[2].address

    with reverts("EMPTY_DATA"):
        factory.createEVMScript(trusted_caller, make_call_data([], []))

    with reverts("LENGTH_MISMATCH"):
        factory.createEVMScript(trusted_caller, make_call_data([recipient], []))

    with reverts("LENGTH_MISMATCH"):
        factory.createEVMScript(trusted_caller, make_call_data([], [123]))


def test_fail_create_evm_script_if_not_trusted_caller(top_up_allowed_recipients, stranger):
    with reverts(""):
        top_up_allowed_recipients.createEVMScript(stranger, make_call_data([], []))


def test_decode_evm_script_call_data(top_up_allowed_recipients, accounts):
    recipient = accounts[4].address
    payout = int(1e18)
    call_data = make_call_data([recipient], [payout])

    assert top_up_allowed_recipients.decodeEVMScriptCallData(call_data) == [[recipient], [payout]]
