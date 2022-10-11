from brownie import ZERO_ADDRESS, reverts
from eth_abi import encode_single


def test_deploy(owner, RemoveAllowedRecipient, allowed_recipients_registry):
    "Must deploy contract with correct data"
    (registry, _, _, _, _, _) = allowed_recipients_registry
    contract = owner.deploy(RemoveAllowedRecipient, owner, registry)

    assert contract.trustedCaller() == owner
    assert contract.allowedRecipientsRegistry() == registry


def test_deploy_zero_trusted_caller(owner, RemoveAllowedRecipient, allowed_recipients_registry):
    "Must revert deploying a contract with zero trusted caller"
    (registry, _, _, _, _, _) = allowed_recipients_registry

    with reverts("TRUSTED_CALLER_IS_ZERO_ADDRESS"):
        owner.deploy(RemoveAllowedRecipient, ZERO_ADDRESS, registry)


def test_deploy_zero_allowed_recipient_registry(owner, RemoveAllowedRecipient):
    "Must deploy contract with zero allowed recipient registry"
    contract = owner.deploy(RemoveAllowedRecipient, owner, ZERO_ADDRESS)
    assert contract.allowedRecipientsRegistry() == ZERO_ADDRESS


def test_create_evm_script_is_permissionless(
    owner, stranger, remove_allowed_recipients, allowed_recipients_registry
):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    registry.addRecipient(stranger, "Stranger", {"from": add_recipient_role_holder})
    call_data = create_calldata(stranger.address)
    remove_allowed_recipients.createEVMScript(owner, call_data, {"from": stranger})


def test_decode_evm_script_calldata_is_permissionless(stranger, remove_allowed_recipients):
    call_data = create_calldata(stranger.address)
    remove_allowed_recipients.decodeEVMScriptCallData(call_data, {"from": stranger})


def test_only_trusted_caller_can_be_creator(
    owner, stranger, remove_allowed_recipients, allowed_recipients_registry
):
    (registry, _, add_recipient_role_holder, _, _, _) = allowed_recipients_registry
    registry.addRecipient(stranger, "Stranger", {"from": add_recipient_role_holder})
    call_data = create_calldata(stranger.address)

    with reverts("CALLER_IS_FORBIDDEN"):
        remove_allowed_recipients.createEVMScript(stranger, call_data, {"from": owner})

    remove_allowed_recipients.createEVMScript(owner, call_data, {"from": owner})


def test_revert_create_evm_script_with_empty_calldata(owner, remove_allowed_recipients):
    with reverts():
        remove_allowed_recipients.createEVMScript(owner, "0x", {"from": owner})


def test_decode_evm_script_calldata_correctly(owner, remove_allowed_recipients):
    call_data = create_calldata(owner.address)

    address = remove_allowed_recipients.decodeEVMScriptCallData(call_data)
    assert address == owner.address


def create_calldata(recipient):
    return encode_single("(address)", [recipient])
