import pytest
from brownie import reverts, SocializeBadDebtInVaultHub, SocializeBadDebtAdapter, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(bad_debt_vaults, vault_acceptors, max_shares_to_socialize):
    return encode_calldata(
        ["address[]", "address[]", "uint256[]"],
        [bad_debt_vaults, vault_acceptors, max_shares_to_socialize]
    )

@pytest.fixture(scope="module")
def socialize_bad_debt_factory(owner, adapter):
    factory = SocializeBadDebtInVaultHub.deploy(owner, adapter, {"from": owner})
    return factory

@pytest.fixture(scope="module")
def adapter(owner, vault_hub_stub):
    adapter = SocializeBadDebtAdapter.deploy(vault_hub_stub, owner, {"from": owner})
    return adapter

def test_deploy(owner, adapter, socialize_bad_debt_factory):
    "Must deploy contract with correct data"
    assert socialize_bad_debt_factory.trustedCaller() == owner
    assert socialize_bad_debt_factory.adapter() == adapter

def test_create_evm_script_called_by_stranger(stranger, socialize_bad_debt_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        socialize_bad_debt_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, socialize_bad_debt_factory):
    "Must revert with message 'Empty bad debt vaults array' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [], [])
    with reverts('Empty bad debt vaults array'):
        socialize_bad_debt_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, socialize_bad_debt_factory):
    "Must revert with message 'Array length mismatch' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [stranger.address, stranger.address], [100])
    with reverts('Array length mismatch'):
        socialize_bad_debt_factory.createEVMScript(owner, CALLDATA)

def test_zero_bad_debt_vault_address(owner, stranger, socialize_bad_debt_factory):
    "Must revert with message 'Zero bad debt vault address' if any bad debt vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [stranger.address, stranger.address], [100, 200])
    with reverts('Zero bad debt vault address'):
        socialize_bad_debt_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_acceptor_address(owner, stranger, socialize_bad_debt_factory):
    "Must revert with message 'Zero vault acceptor address' if any vault acceptor is zero address"
    CALLDATA = create_calldata([stranger.address, stranger.address], [ZERO_ADDRESS, stranger.address], [100, 200])
    with reverts('Zero vault acceptor address'):
        socialize_bad_debt_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, socialize_bad_debt_factory, adapter):
    "Must create correct EVMScript if all requirements are met"
    bad_debt_vault1 = accounts[5]
    bad_debt_vault2 = accounts[6]
    vault_acceptor1 = accounts[7]
    vault_acceptor2 = accounts[8]
    
    bad_debt_vaults = [bad_debt_vault1.address, bad_debt_vault2.address]
    vault_acceptors = [vault_acceptor1.address, vault_acceptor2.address]
    max_shares_to_socialize = [100, 200]
    
    EVM_SCRIPT_CALLDATA = create_calldata(bad_debt_vaults, vault_acceptors, max_shares_to_socialize)
    evm_script = socialize_bad_debt_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each vault
    expected_calls = []
    for i in range(len(bad_debt_vaults)):
        expected_calls.append((
            adapter.address,
            adapter.socializeBadDebt.encode_input(
                bad_debt_vaults[i],
                vault_acceptors[i],
                max_shares_to_socialize[i]
            )
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(accounts, socialize_bad_debt_factory):
    "Must decode EVMScript call data correctly"
    bad_debt_vaults = [accounts[5].address, accounts[6].address]
    vault_acceptors = [accounts[7].address, accounts[8].address]
    max_shares_to_socialize = [100, 200]
    EVM_SCRIPT_CALLDATA = create_calldata(bad_debt_vaults, vault_acceptors, max_shares_to_socialize)
    decoded_bad_debt_vaults, decoded_vault_acceptors, decoded_max_shares = socialize_bad_debt_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert len(decoded_bad_debt_vaults) == len(bad_debt_vaults)
    assert len(decoded_vault_acceptors) == len(vault_acceptors)
    assert len(decoded_max_shares) == len(max_shares_to_socialize)
    for i in range(len(bad_debt_vaults)):
        assert decoded_bad_debt_vaults[i] == bad_debt_vaults[i]
        assert decoded_vault_acceptors[i] == vault_acceptors[i]
        assert decoded_max_shares[i] == max_shares_to_socialize[i] 
