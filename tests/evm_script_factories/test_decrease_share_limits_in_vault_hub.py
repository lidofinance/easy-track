import pytest
from brownie import reverts, DecreaseShareLimitsInVaultHub, VaultHubAdapter, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, share_limits):
    return encode_calldata(["address[]", "uint256[]"], [vaults, share_limits])

@pytest.fixture(scope="module")
def adapter(owner, vault_hub_stub):
    adapter = VaultHubAdapter.deploy(owner, vault_hub_stub, owner, 1000000000000000000, {"from": owner})
    return adapter

@pytest.fixture(scope="module")
def update_share_limits_factory(owner, adapter):
    factory = DecreaseShareLimitsInVaultHub.deploy(owner, adapter, {"from": owner})
    return factory

def test_deploy(owner, update_share_limits_factory, adapter, vault_hub_stub):
    "Must deploy contract with correct data"
    assert update_share_limits_factory.trustedCaller() == owner
    assert update_share_limits_factory.vaultHubAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == owner
    assert adapter.evmScriptExecutor() == owner

def test_create_evm_script_called_by_stranger(stranger, update_share_limits_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_share_limits_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, update_share_limits_factory):
    "Must revert with message 'EMPTY_VAULTS' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_VAULTS'):
        update_share_limits_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, update_share_limits_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [1000, 2000])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        update_share_limits_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_address(owner, stranger, update_share_limits_factory):
    "Must revert with message 'ZERO_VAULT' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [1000, 2000])
    with reverts('ZERO_VAULT'):
        update_share_limits_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, update_share_limits_factory, adapter):
    "Must create correct EVMScript if all requirements are met"
    # Register vaults first
    vault1 = accounts[5]
    vault2 = accounts[6]
    
    vaults = [vault1.address, vault2.address]
    share_limits = [500, 500]
    
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, share_limits)
    evm_script = update_share_limits_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each vault
    expected_calls = []
    for i in range(len(vaults)):
        expected_calls.append((
            adapter.address,
            adapter.updateShareLimit.encode_input(vaults[i], share_limits[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(accounts, update_share_limits_factory):
    "Must decode EVMScript call data correctly"
    vaults = [accounts[5].address, accounts[6].address]
    share_limits = [1000, 2000]
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, share_limits)
    decoded_vaults, decoded_share_limits = update_share_limits_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert len(decoded_vaults) == len(vaults)
    assert len(decoded_share_limits) == len(share_limits)
    for i in range(len(vaults)):
        assert decoded_vaults[i] == vaults[i]
        assert decoded_share_limits[i] == share_limits[i]
