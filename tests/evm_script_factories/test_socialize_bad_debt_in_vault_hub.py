import pytest
from brownie import interface, reverts, SocializeBadDebtInVaultHub, VaultsAdapter, StakingVaultStub, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(bad_debt_vaults, vault_acceptors, max_shares_to_socialize):
    return encode_calldata(
        ["address[]", "address[]", "uint256[]"],
        [bad_debt_vaults, vault_acceptors, max_shares_to_socialize]
    )

@pytest.fixture(scope="module")
def adapter(owner, lido_locator_stub):
    adapter = VaultsAdapter.deploy(owner, lido_locator_stub, owner, 1000000000000000000, {"from": owner})
    return adapter

@pytest.fixture(scope="module")
def socialize_bad_debt_factory(owner, adapter):
    factory = SocializeBadDebtInVaultHub.deploy(owner, adapter, {"from": owner})
    return factory

def test_deploy(owner, socialize_bad_debt_factory, adapter, lido_locator_stub):
    "Must deploy contract with correct data"
    assert socialize_bad_debt_factory.trustedCaller() == owner
    assert socialize_bad_debt_factory.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == owner
    assert adapter.evmScriptExecutor() == owner
    assert adapter.lidoLocator() == lido_locator_stub

def test_create_evm_script_called_by_stranger(stranger, socialize_bad_debt_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        socialize_bad_debt_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_bad_debt_vaults_array(owner, socialize_bad_debt_factory):
    "Must revert with message 'EMPTY_BAD_DEBT_VAULTS' if bad debt vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [], [])
    with reverts('EMPTY_BAD_DEBT_VAULTS'):
        socialize_bad_debt_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, socialize_bad_debt_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [stranger.address, stranger.address], [100])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        socialize_bad_debt_factory.createEVMScript(owner, CALLDATA)

def test_zero_bad_debt_vault_address(owner, stranger, socialize_bad_debt_factory):
    "Must revert with message 'ZERO_BAD_DEBT_VAULT' if any bad debt vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [stranger.address, stranger.address], [100, 200])
    with reverts('ZERO_BAD_DEBT_VAULT'):
        socialize_bad_debt_factory.createEVMScript(owner, CALLDATA)

def test_zero_vault_acceptor_address(owner, stranger, socialize_bad_debt_factory):
    "Must revert with message 'ZERO_VAULT_ACCEPTOR' if any vault acceptor is zero address"
    CALLDATA = create_calldata([stranger.address, stranger.address], [ZERO_ADDRESS, stranger.address], [100, 200])
    with reverts('ZERO_VAULT_ACCEPTOR'):
        socialize_bad_debt_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, accounts, socialize_bad_debt_factory, adapter):
    "Must create correct EVMScript if all requirements are met"
    bad_debt_vault1 = StakingVaultStub.deploy(accounts[5], {"from": owner})
    bad_debt_vault2 = StakingVaultStub.deploy(accounts[6], {"from": owner})
    vault_acceptor1 = StakingVaultStub.deploy(accounts[5], {"from": owner})
    vault_acceptor2 = StakingVaultStub.deploy(accounts[6], {"from": owner})

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

def test_socialize_bad_debt_fails_when_bad_debt_vault_not_connected(owner, accounts, adapter, lido_locator_stub):
    "Must emit BadDebtSocializationFailed when bad debt vault is not connected to hub"
    vault_hub = interface.IVaultHub(lido_locator_stub.vaultHub())
    bad_debt_vault = accounts[5]
    vault_acceptor = accounts[6]
    max_shares_to_socialize = 100

    # Connect only vault_acceptor, not bad_debt_vault
    vault_hub.connectVault(vault_acceptor, {"from": owner})

    # Verify bad_debt_vault is NOT connected
    assert vault_hub.isVaultConnected(bad_debt_vault) == False
    # Verify vault_acceptor IS connected
    assert vault_hub.isVaultConnected(vault_acceptor) == True

    # Try to socialize bad debt - should fail
    tx = adapter.socializeBadDebt(bad_debt_vault, vault_acceptor, max_shares_to_socialize, {"from": owner})

    # Should emit BadDebtSocializationFailed event
    assert "BadDebtSocializationFailed" in tx.events
    assert tx.events["BadDebtSocializationFailed"]["badDebtVault"] == bad_debt_vault
    assert tx.events["BadDebtSocializationFailed"]["vaultAcceptor"] == vault_acceptor
    assert tx.events["BadDebtSocializationFailed"]["maxSharesToSocialize"] == max_shares_to_socialize

def test_socialize_bad_debt_fails_when_vault_acceptor_not_connected(owner, accounts, adapter, lido_locator_stub):
    "Must emit BadDebtSocializationFailed when vault acceptor is not connected to hub"
    vault_hub = interface.IVaultHub(lido_locator_stub.vaultHub())
    bad_debt_vault = accounts[5]
    vault_acceptor = accounts[6]
    max_shares_to_socialize = 100

    # Connect only bad_debt_vault, not vault_acceptor
    vault_hub.connectVault(bad_debt_vault, {"from": owner})

    # Verify bad_debt_vault IS connected
    assert vault_hub.isVaultConnected(bad_debt_vault) == True
    # Verify vault_acceptor is NOT connected
    assert vault_hub.isVaultConnected(vault_acceptor) == False

    # Try to socialize bad debt - should fail
    tx = adapter.socializeBadDebt(bad_debt_vault, vault_acceptor, max_shares_to_socialize, {"from": owner})

    # Should emit BadDebtSocializationFailed event
    assert "BadDebtSocializationFailed" in tx.events
    assert tx.events["BadDebtSocializationFailed"]["badDebtVault"] == bad_debt_vault
    assert tx.events["BadDebtSocializationFailed"]["vaultAcceptor"] == vault_acceptor
    assert tx.events["BadDebtSocializationFailed"]["maxSharesToSocialize"] == max_shares_to_socialize
