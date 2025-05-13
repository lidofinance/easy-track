import pytest
from brownie import reverts, UpdateShareLimitsInVaultHub, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, share_limits):
    return encode_calldata(["address[]", "uint256[]"], [vaults, share_limits])

@pytest.fixture(scope="module")
def update_share_limits_factory(owner, vault_hub_stub):
    factory = UpdateShareLimitsInVaultHub.deploy(owner, vault_hub_stub, {"from": owner})
    vault_hub_stub.grantRole(vault_hub_stub.VAULT_MASTER_ROLE(), factory, {"from": owner})
    return factory

def test_deploy(owner, vault_hub_stub, update_share_limits_factory):
    "Must deploy contract with correct data"
    assert update_share_limits_factory.trustedCaller() == owner
    assert update_share_limits_factory.vaultHub() == vault_hub_stub

def test_create_evm_script_called_by_stranger(stranger, update_share_limits_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_share_limits_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, update_share_limits_factory):
    "Must revert with message 'Empty vaults array' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('Empty vaults array'):
        update_share_limits_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, update_share_limits_factory):
    "Must revert with message 'Array length mismatch' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [1000, 2000])
    with reverts('Array length mismatch'):
        update_share_limits_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_address(owner, stranger, update_share_limits_factory):
    "Must revert with message 'Zero vault address' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [1000, 2000])
    with reverts('Zero vault address'):
        update_share_limits_factory.createEVMScript(owner, CALLDATA)

def test_vault_not_registered(owner, stranger, accounts, update_share_limits_factory):
    "Must revert with message 'Vault not registered' if any vault is not registered"
    CALLDATA = create_calldata([stranger.address, accounts[5].address], [1000, 2000])
    with reverts('Vault not registered'):
        update_share_limits_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, update_share_limits_factory, vault_hub_stub):
    "Must create correct EVMScript if all requirements are met"
    # Register vaults first
    vault1 = accounts[5]
    vault2 = accounts[6]
    vault_hub_stub.connectVault(vault1)
    vault_hub_stub.connectVault(vault2)
    
    vaults = [vault1.address, vault2.address]
    share_limits = [2000, 3000]
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, share_limits)
    evm_script = update_share_limits_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript
    update_share_limits_calldata = vault_hub_stub.updateShareLimits.encode_input(vaults, share_limits)
    expected_evm_script = encode_call_script([
        (vault_hub_stub.address, update_share_limits_calldata)
    ])

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