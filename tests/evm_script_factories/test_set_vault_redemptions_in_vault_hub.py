import pytest
from brownie import reverts, SetVaultRedemptionsInVaultHub, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, redemptions_values):
    return encode_calldata(["address[]", "uint256[]"], [vaults, redemptions_values])

@pytest.fixture(scope="module")
def set_vault_redemptions_factory(owner, vault_hub_stub):
    factory = SetVaultRedemptionsInVaultHub.deploy(owner, vault_hub_stub, {"from": owner})
    return factory

def test_deploy(owner, vault_hub_stub, set_vault_redemptions_factory):
    "Must deploy contract with correct data"
    assert set_vault_redemptions_factory.trustedCaller() == owner
    assert set_vault_redemptions_factory.vaultHub() == vault_hub_stub

def test_create_evm_script_called_by_stranger(stranger, set_vault_redemptions_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_vault_redemptions_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, set_vault_redemptions_factory):
    "Must revert with message 'EMPTY_VAULTS' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_VAULTS'):
        set_vault_redemptions_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, set_vault_redemptions_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [100, 200])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        set_vault_redemptions_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_address(owner, stranger, set_vault_redemptions_factory):
    "Must revert with message 'ZERO_VAULT' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [100, 200])
    with reverts('ZERO_VAULT'):
        set_vault_redemptions_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, set_vault_redemptions_factory, vault_hub_stub):
    "Must create correct EVMScript if all requirements are met"
    vault1 = accounts[5]
    vault2 = accounts[6]
    
    vaults = [vault1.address, vault2.address]
    redemptions_values = [100, 200]
    
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, redemptions_values)
    evm_script = set_vault_redemptions_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each vault
    expected_calls = []
    for i in range(len(vaults)):
        expected_calls.append((
            vault_hub_stub.address,
            vault_hub_stub.setVaultRedemptions.encode_input(vaults[i], redemptions_values[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(accounts, set_vault_redemptions_factory):
    "Must decode EVMScript call data correctly"
    vaults = [accounts[5].address, accounts[6].address]
    redemptions_values = [100, 200]
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, redemptions_values)
    decoded_vaults, decoded_redemptions_values = set_vault_redemptions_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert len(decoded_vaults) == len(vaults)
    assert len(decoded_redemptions_values) == len(redemptions_values)
    for i in range(len(vaults)):
        assert decoded_vaults[i] == vaults[i]
        assert decoded_redemptions_values[i] == redemptions_values[i] 
