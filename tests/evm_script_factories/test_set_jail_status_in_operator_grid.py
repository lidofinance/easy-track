import pytest
from brownie import reverts, SetJailStatusInOperatorGrid, VaultsAdapter, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, jail_statuses):
    return encode_calldata(["address[]", "bool[]"], [vaults, jail_statuses])

@pytest.fixture(scope="module")
def adapter(owner, vault_hub_stub, operator_grid_stub):
    adapter = VaultsAdapter.deploy(owner, vault_hub_stub, operator_grid_stub, owner, 1000000000000000000, {"from": owner})
    return adapter

@pytest.fixture(scope="module")
def set_jail_status_factory(owner, adapter):
    factory = SetJailStatusInOperatorGrid.deploy(owner, adapter, {"from": owner})
    return factory

def test_deploy(owner, set_jail_status_factory, adapter, vault_hub_stub):
    "Must deploy contract with correct data"
    assert set_jail_status_factory.trustedCaller() == owner
    assert set_jail_status_factory.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == owner
    assert adapter.evmScriptExecutor() == owner

def test_create_evm_script_called_by_stranger(stranger, set_jail_status_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_jail_status_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, set_jail_status_factory):
    "Must revert with message 'EMPTY_VAULTS' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_VAULTS'):
        set_jail_status_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, set_jail_status_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [True, False])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        set_jail_status_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_address(owner, stranger, set_jail_status_factory):
    "Must revert with message 'ZERO_VAULT' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [True, False])
    with reverts('ZERO_VAULT'):
        set_jail_status_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, set_jail_status_factory, adapter):
    "Must create correct EVMScript if all requirements are met"
    vault1 = accounts[5]
    vault2 = accounts[6]

    vaults = [vault1.address, vault2.address]
    jail_statuses = [True, False]

    EVM_SCRIPT_CALLDATA = create_calldata(vaults, jail_statuses)
    evm_script = set_jail_status_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each vault
    expected_calls = []
    for i in range(len(vaults)):
        expected_calls.append((
            adapter.address,
            adapter.setVaultJailStatus.encode_input(vaults[i], jail_statuses[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_same_jail_status_fails(owner, accounts, adapter, operator_grid_stub, vault_hub_stub):
    "Must emit VaultJailStatusUpdateFailed if current status equals new status"
    vault = accounts[5]

    # Connect vault first
    vault_hub_stub.connectVault(vault)

    # Set initial jail status to True
    operator_grid_stub.setVaultJailStatus(vault, True, {"from": owner})

    # Try to set the same status again - should fail
    tx = adapter.setVaultJailStatus(vault, True, {"from": owner})

    # Check that VaultJailStatusUpdateFailed event was emitted
    assert "VaultJailStatusUpdateFailed" in tx.events
    assert tx.events["VaultJailStatusUpdateFailed"]["vault"] == vault
    assert tx.events["VaultJailStatusUpdateFailed"]["isInJail"] == True

def test_decode_evm_script_call_data(accounts, set_jail_status_factory):
    "Must decode EVMScript call data correctly"
    vaults = [accounts[5].address, accounts[6].address]
    jail_statuses = [True, False]
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, jail_statuses)
    decoded_vaults, decoded_jail_statuses = set_jail_status_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert len(decoded_vaults) == len(vaults)
    assert len(decoded_jail_statuses) == len(jail_statuses)
    for i in range(len(vaults)):
        assert decoded_vaults[i] == vaults[i]
        assert decoded_jail_statuses[i] == jail_statuses[i]
