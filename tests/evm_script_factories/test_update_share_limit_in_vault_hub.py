import pytest
from brownie import reverts, UpdateShareLimitInVaultHub, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vault, share_limit):
    return encode_calldata(["address", "uint256"], [vault, share_limit])

@pytest.fixture(scope="module")
def update_share_limit_factory(owner, vault_hub_stub):
    factory = UpdateShareLimitInVaultHub.deploy(owner, vault_hub_stub, {"from": owner})
    vault_hub_stub.grantRole(vault_hub_stub.VAULT_MASTER_ROLE(), factory, {"from": owner})
    return factory

def test_deploy(owner, vault_hub_stub, update_share_limit_factory):
    "Must deploy contract with correct data"
    assert update_share_limit_factory.trustedCaller() == owner
    assert update_share_limit_factory.vaultHub() == vault_hub_stub

def test_create_evm_script_called_by_stranger(stranger, update_share_limit_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_share_limit_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_zero_vault_address(owner, update_share_limit_factory):
    "Must revert with message 'Zero vault address' if vault is zero address"
    EMPTY_CALLDATA = create_calldata(ZERO_ADDRESS, 1000)
    with reverts('Zero vault address'):
        update_share_limit_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_vault_not_registered(owner, stranger, update_share_limit_factory):
    "Must revert with message 'Vault not registered' if vault is not registered"
    CALLDATA = create_calldata(stranger.address, 1000)
    with reverts('Vault not registered'):
        update_share_limit_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, stranger, update_share_limit_factory, vault_hub_stub):
    "Must create correct EVMScript if all requirements are met"
    # Register vault first
    vault_hub_stub.connectVault(stranger)
    
    input_params = [stranger.address, 2000]
    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    evm_script = update_share_limit_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript
    update_share_limit_calldata = vault_hub_stub.updateShareLimit.encode_input(input_params[0], input_params[1])
    expected_evm_script = encode_call_script([
        (vault_hub_stub.address, update_share_limit_calldata)
    ])

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(stranger, update_share_limit_factory):
    "Must decode EVMScript call data correctly"
    input_params = [stranger.address, 1000]
    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    decoded_params = update_share_limit_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert decoded_params[0] == input_params[0]  # vault
    assert decoded_params[1] == input_params[1]  # shareLimit 