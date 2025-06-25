import pytest
from brownie import reverts, ForceValidatorExitsInVaultHub, VaultHubAdapter, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, pubkeys):
    return encode_calldata(["address[]", "bytes[]"], [vaults, pubkeys])

@pytest.fixture(scope="module")
def adapter(owner, vault_hub_stub):
    adapter = VaultHubAdapter.deploy(owner, vault_hub_stub, owner, 1000000000000000000, {"from": owner})
    # send 10 ETH to adapter
    owner.transfer(adapter, 10 * 10 ** 18)
    return adapter

@pytest.fixture(scope="module")
def force_validator_exits_factory(owner, adapter):
    factory = ForceValidatorExitsInVaultHub.deploy(owner, adapter, {"from": owner})
    return factory

def test_deploy(owner, force_validator_exits_factory, adapter, vault_hub_stub):
    "Must deploy contract with correct data"
    assert force_validator_exits_factory.trustedCaller() == owner
    assert force_validator_exits_factory.vaultHubAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == owner
    assert adapter.evmScriptExecutor() == owner

def test_create_evm_script_called_by_stranger(stranger, force_validator_exits_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        force_validator_exits_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, force_validator_exits_factory):
    "Must revert with message 'EMPTY_VAULTS' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_VAULTS'):
        force_validator_exits_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, force_validator_exits_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [b"0x" * 48, b"0x" * 48])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        force_validator_exits_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_address(owner, stranger, force_validator_exits_factory):
    "Must revert with message 'ZERO_VAULT' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [b"0x" * 48, b"0x" * 48])
    with reverts('ZERO_VAULT'):
        force_validator_exits_factory.createEVMScript(owner, CALLDATA)

def test_empty_pubkeys(owner, stranger, force_validator_exits_factory):
    "Must revert with message 'EMPTY_PUBKEYS' if any pubkeys array is empty"
    CALLDATA = create_calldata([stranger.address], [b""])
    with reverts('EMPTY_PUBKEYS'):
        force_validator_exits_factory.createEVMScript(owner, CALLDATA)

def test_invalid_pubkeys_length(owner, stranger, force_validator_exits_factory):
    "Must revert with message 'INVALID_PUBKEYS_LENGTH' if pubkeys length is not multiple of 48"
    CALLDATA = create_calldata([stranger.address], [b"0x" * 47])
    with reverts('INVALID_PUBKEYS_LENGTH'):
        force_validator_exits_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, force_validator_exits_factory, adapter):
    "Must create correct EVMScript if all requirements are met"
    vault1 = accounts[5]
    vault2 = accounts[6]
    
    vaults = [vault1.address, vault2.address]
    pubkeys = [b"01" * 48, b"02" * 48]  # 48 bytes per pubkey
    
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, pubkeys)
    evm_script = force_validator_exits_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each vault
    expected_calls = []
    for i in range(len(vaults)):
        expected_calls.append((
            adapter.address,
            adapter.forceValidatorExit.encode_input(vaults[i], pubkeys[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(accounts, force_validator_exits_factory):
    "Must decode EVMScript call data correctly"
    vaults = [accounts[5].address, accounts[6].address]
    pubkeys = [b"01" * 48, b"02" * 48]
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, pubkeys)
    decoded_vaults, decoded_pubkeys = force_validator_exits_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert len(decoded_vaults) == len(vaults)
    assert len(decoded_pubkeys) == len(pubkeys)
    for i in range(len(vaults)):
        assert decoded_vaults[i] == vaults[i]
        assert decoded_pubkeys[i] == "0x" + pubkeys[i].hex()

def test_withdraw_eth_called_by_stranger(stranger, adapter):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if caller isn't trustedCaller"
    with reverts():
        adapter.withdrawETH(stranger.address, {"from": stranger})

def test_withdraw_eth_no_balance(owner, adapter):
    "Must revert with message 'No ETH to withdraw' if contract has no ETH balance"
    adapter.withdrawETH(owner.address, {"from": owner})
    with reverts():
        adapter.withdrawETH(owner.address, {"from": owner})

def test_withdraw_eth_success(owner, adapter):
    "Must successfully withdraw ETH to trusted caller"
    # Send some ETH to the adapter
    owner.transfer(adapter, "1 ether")
    
    # Get initial balances
    initial_owner_balance = owner.balance()
    initial_balance = adapter.balance()
    
    # Withdraw ETH
    tx = adapter.withdrawETH(owner.address, {"from": owner})
    
    # Check final balances
    assert adapter.balance() == 0, "Factory should have 0 ETH after withdrawal"
    # Account for gas costs in the owner's final balance
    gas_cost = tx.gas_used * tx.gas_price
    assert owner.balance() == initial_owner_balance + initial_balance - gas_cost, "Owner should receive all ETH minus gas costs"
    
    # Check event
    assert len(tx.events) == 0, "No events should be emitted"
