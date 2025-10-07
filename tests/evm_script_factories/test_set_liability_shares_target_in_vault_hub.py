import pytest
from brownie import reverts, SetLiabilitySharesTargetInVaultHub, VaultsAdapter, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, liability_shares_targets):
    return encode_calldata(["address[]", "uint256[]"], [vaults, liability_shares_targets])

@pytest.fixture(scope="module")
def adapter(owner, lido_locator_stub):
    adapter = VaultsAdapter.deploy(owner, lido_locator_stub, owner, 1000000000000000000, {"from": owner})
    return adapter

@pytest.fixture(scope="module")
def set_liability_shares_target_factory(owner, adapter):
    factory = SetLiabilitySharesTargetInVaultHub.deploy(owner, adapter, {"from": owner})
    return factory

def test_deploy(owner, set_liability_shares_target_factory, adapter, lido_locator_stub):
    "Must deploy contract with correct data"
    assert set_liability_shares_target_factory.trustedCaller() == owner
    assert set_liability_shares_target_factory.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == owner
    assert adapter.evmScriptExecutor() == owner
    assert adapter.lidoLocator() == lido_locator_stub

def test_create_evm_script_called_by_stranger(stranger, set_liability_shares_target_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_liability_shares_target_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, set_liability_shares_target_factory):
    "Must revert with message 'EMPTY_VAULTS' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_VAULTS'):
        set_liability_shares_target_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, set_liability_shares_target_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [100, 200])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        set_liability_shares_target_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_address(owner, stranger, set_liability_shares_target_factory):
    "Must revert with message 'ZERO_VAULT' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [100, 200])
    with reverts('ZERO_VAULT'):
        set_liability_shares_target_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, set_liability_shares_target_factory, adapter):
    "Must create correct EVMScript if all requirements are met"
    vault1 = accounts[5]
    vault2 = accounts[6]

    vaults = [vault1.address, vault2.address]
    liability_shares_targets = [100, 200]

    EVM_SCRIPT_CALLDATA = create_calldata(vaults, liability_shares_targets)
    evm_script = set_liability_shares_target_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each vault
    expected_calls = []
    for i in range(len(vaults)):
        expected_calls.append((
            adapter.address,
            adapter.setLiabilitySharesTarget.encode_input(vaults[i], liability_shares_targets[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(accounts, set_liability_shares_target_factory):
    "Must decode EVMScript call data correctly"
    vaults = [accounts[5].address, accounts[6].address]
    liability_shares_targets = [100, 200]
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, liability_shares_targets)
    decoded_vaults, decoded_liability_shares_targets = set_liability_shares_target_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert len(decoded_vaults) == len(vaults)
    assert len(decoded_liability_shares_targets) == len(liability_shares_targets)
    for i in range(len(vaults)):
        assert decoded_vaults[i] == vaults[i]
        assert decoded_liability_shares_targets[i] == liability_shares_targets[i]
