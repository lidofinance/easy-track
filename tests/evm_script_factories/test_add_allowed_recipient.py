from brownie import ZERO_ADDRESS, reverts
from utils.evm_script import encode_calldata, encode_call_script
from utils.hardhat_helpers import get_last_tx_revert_reason

EVM_SCRIPT_CALLDATA_TITLE = "TITLE"


def test_deploy(owner, AddAllowedRecipient, allowed_recipients_registry):
    "Must deploy contract with correct data"
    (registry, _, _, _, _, _) = allowed_recipients_registry
    contract = owner.deploy(AddAllowedRecipient, owner, registry)

    assert contract.trustedCaller() == owner
    assert contract.allowedRecipientsRegistry() == registry


def test_deploy_zero_trusted_caller(owner, AddAllowedRecipient, allowed_recipients_registry):
    "Must revert deploying a contract with zero trusted caller"
    (registry, _, _, _, _, _) = allowed_recipients_registry

    revert_reason = "TRUSTED_CALLER_IS_ZERO_ADDRESS"
    try:
        with reverts(revert_reason):
            owner.deploy(AddAllowedRecipient, ZERO_ADDRESS, registry)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e


def test_deploy_zero_allowed_recipient_registry(owner, AddAllowedRecipient):
    "Must deploy contract with zero allowed recipient registry"
    contract = owner.deploy(AddAllowedRecipient, owner, ZERO_ADDRESS)

    assert contract.allowedRecipientsRegistry() == ZERO_ADDRESS


def test_create_evm_script_is_permissionless(owner, stranger, add_allowed_recipients):
    call_data = create_calldata(owner.address)
    add_allowed_recipients.createEVMScript(owner, call_data, {"from": stranger})


def test_decode_evm_script_calldata_is_permissionless(stranger, add_allowed_recipients):
    call_data = create_calldata(stranger.address)
    add_allowed_recipients.decodeEVMScriptCallData(call_data, {"from": stranger})


def test_only_trusted_caller_can_be_creator(owner, stranger, add_allowed_recipients):
    call_data = create_calldata(owner.address)

    with reverts("CALLER_IS_FORBIDDEN"):
        add_allowed_recipients.createEVMScript(stranger, call_data, {"from": owner})

    add_allowed_recipients.createEVMScript(owner, call_data, {"from": owner})


def test_revert_create_evm_script_with_empty_calldata(owner, add_allowed_recipients):
    with reverts():
        add_allowed_recipients.createEVMScript(owner, "0x", {"from": owner})


def test_revert_create_evm_script_with_empty_recipient_address(owner, add_allowed_recipients):
    call_data = create_calldata(ZERO_ADDRESS)
    with reverts("RECIPIENT_ADDRESS_IS_ZERO_ADDRESS"):
        add_allowed_recipients.createEVMScript(owner, call_data, {"from": owner})


def test_revert_recipient_already_added(owner, stranger, add_allowed_recipients, allowed_recipients_registry):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    registry.addRecipient(stranger, "Stranger", {"from": add_recipient_role_holder})
    call_data = create_calldata(stranger.address)

    with reverts("ALLOWED_RECIPIENT_ALREADY_ADDED"):
        add_allowed_recipients.createEVMScript(owner, call_data)


def test_create_evm_script_correctly(owner, add_allowed_recipients, allowed_recipients_registry):
    call_data = create_calldata(owner.address)
    evm_script = add_allowed_recipients.createEVMScript(owner, call_data)
    (registry, _, _, _, _, _) = allowed_recipients_registry
    expected_evm_script = encode_call_script(
        [
            (
                registry.address,
                registry.addRecipient.encode_input(owner, EVM_SCRIPT_CALLDATA_TITLE),
            )
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_calldata_correctly(owner, add_allowed_recipients):
    call_data = create_calldata(owner.address)

    (address, title) = add_allowed_recipients.decodeEVMScriptCallData(call_data)
    assert address == owner.address
    assert title == EVM_SCRIPT_CALLDATA_TITLE


def create_calldata(recipient):
    return encode_calldata(["address", "string"], [recipient, EVM_SCRIPT_CALLDATA_TITLE])
