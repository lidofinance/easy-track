import pytest
from brownie import reverts, UpdateVaultsFeesInVaultHub, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp):
    return encode_calldata(
        ["address[]", "uint256[]", "uint256[]", "uint256[]"], 
        [vaults, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp]
    )

@pytest.fixture(scope="module")
def update_vaults_fees_factory(owner, vault_hub_stub):
    factory = UpdateVaultsFeesInVaultHub.deploy(owner, vault_hub_stub, {"from": owner})
    vault_hub_stub.grantRole(vault_hub_stub.VAULT_MASTER_ROLE(), factory, {"from": owner})
    return factory

def test_deploy(owner, vault_hub_stub, update_vaults_fees_factory):
    "Must deploy contract with correct data"
    assert update_vaults_fees_factory.trustedCaller() == owner
    assert update_vaults_fees_factory.vaultHub() == vault_hub_stub

def test_create_evm_script_called_by_stranger(stranger, update_vaults_fees_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_vaults_fees_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, update_vaults_fees_factory):
    "Must revert with message 'Empty vaults array' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [], [], [])
    with reverts('Empty vaults array'):
        update_vaults_fees_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, update_vaults_fees_factory):
    "Must revert with message 'Array length mismatch' if arrays have different lengths"
    # Different lengths for infra fees
    CALLDATA1 = create_calldata([stranger.address], [1000, 2000], [1000], [1000])
    with reverts('Array length mismatch'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA1)
    
    # Different lengths for liquidity fees
    CALLDATA2 = create_calldata([stranger.address], [1000], [1000, 2000], [1000])
    with reverts('Array length mismatch'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA2)
    
    # Different lengths for reservation fees
    CALLDATA3 = create_calldata([stranger.address], [1000], [1000], [1000, 2000])
    with reverts('Array length mismatch'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA3)

def test_zero_vault_address(owner, stranger, update_vaults_fees_factory):
    "Must revert with message 'Zero vault address' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [1000, 1000], [1000, 1000], [1000, 1000])
    with reverts('Zero vault address'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA)

def test_fees_exceed_100_percent(owner, stranger, update_vaults_fees_factory, vault_hub_stub):
    "Must revert if any fee exceeds 100%"
    # Register vault first
    vault_hub_stub.connectVault(stranger)
    
    # Test infra fee exceeds 100%
    CALLDATA1 = create_calldata([stranger.address], [10001], [1000], [1000])
    with reverts('Infra fee BP exceeds 100%'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA1)
    
    # Test liquidity fee exceeds 100%
    CALLDATA2 = create_calldata([stranger.address], [1000], [10001], [1000])
    with reverts('Liquidity fee BP exceeds 100%'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA2)
    
    # Test reservation fee exceeds 100%
    CALLDATA3 = create_calldata([stranger.address], [1000], [1000], [10001])
    with reverts('Reservation fee BP exceeds 100%'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA3)

def test_vault_not_registered(owner, stranger, update_vaults_fees_factory):
    "Must revert with message 'Vault not registered' if any vault is not registered"
    CALLDATA = create_calldata([stranger.address], [1000], [1000], [1000])
    with reverts('Vault not registered'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script_single_vault(owner, stranger, update_vaults_fees_factory, vault_hub_stub):
    "Must create correct EVMScript for a single vault if all requirements are met"
    # Register vault first
    vault_hub_stub.connectVault(stranger)
    
    vaults = [stranger.address]
    infra_fees = [2000]
    liquidity_fees = [3000]
    reservation_fees = [1000]
    
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, infra_fees, liquidity_fees, reservation_fees)
    evm_script = update_vaults_fees_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript
    update_fees_calldata = vault_hub_stub.updateVaultsFees.encode_input(vaults, infra_fees, liquidity_fees, reservation_fees)
    expected_evm_script = encode_call_script([
        (vault_hub_stub.address, update_fees_calldata)
    ])

    assert evm_script == expected_evm_script

def test_create_evm_script_multiple_vaults(owner, accounts, update_vaults_fees_factory, vault_hub_stub):
    "Must create correct EVMScript for multiple vaults if all requirements are met"
    # Register multiple vaults first
    vault1 = accounts[1]
    vault2 = accounts[2]
    vault_hub_stub.connectVault(vault1)
    vault_hub_stub.connectVault(vault2)
    
    vaults = [vault1.address, vault2.address]
    infra_fees = [2000, 1500]
    liquidity_fees = [3000, 2500]
    reservation_fees = [1000, 500]
    
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, infra_fees, liquidity_fees, reservation_fees)
    evm_script = update_vaults_fees_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript
    update_fees_calldata = vault_hub_stub.updateVaultsFees.encode_input(vaults, infra_fees, liquidity_fees, reservation_fees)
    expected_evm_script = encode_call_script([
        (vault_hub_stub.address, update_fees_calldata)
    ])

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(accounts, update_vaults_fees_factory):
    "Must decode EVMScript call data correctly"
    vaults = [accounts[1].address, accounts[2].address]
    infra_fees = [2000, 1500]
    liquidity_fees = [3000, 2500]
    reservation_fees = [1000, 500]
    
    EVM_SCRIPT_CALLDATA = create_calldata(vaults, infra_fees, liquidity_fees, reservation_fees)
    decoded_params = update_vaults_fees_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert decoded_params[0] == vaults  # vaults
    assert decoded_params[1] == infra_fees  # infraFeesBP
    assert decoded_params[2] == liquidity_fees  # liquidityFeesBP
    assert decoded_params[3] == reservation_fees  # reservationFeesBP 