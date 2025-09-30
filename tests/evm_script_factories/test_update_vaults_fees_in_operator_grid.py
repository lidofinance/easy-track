import pytest
from brownie import reverts, UpdateVaultsFeesInOperatorGrid, VaultsAdapter, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(vaults, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp):
    return encode_calldata(
        ["address[]", "uint256[]", "uint256[]", "uint256[]"],
        [vaults, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp]
    )

@pytest.fixture(scope="module")
def adapter(owner, vault_hub_stub, operator_grid_stub):
    adapter = VaultsAdapter.deploy(owner, vault_hub_stub, operator_grid_stub, owner, 1000000000000000000, {"from": owner})
    return adapter

@pytest.fixture(scope="module")
def update_vaults_fees_factory(owner, adapter):
    factory = UpdateVaultsFeesInOperatorGrid.deploy(owner, adapter, {"from": owner})
    return factory

def test_deploy(owner, update_vaults_fees_factory, adapter, vault_hub_stub):
    "Must deploy contract with correct data"
    assert update_vaults_fees_factory.trustedCaller() == owner
    assert update_vaults_fees_factory.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == owner
    assert adapter.evmScriptExecutor() == owner

def test_create_evm_script_called_by_stranger(stranger, update_vaults_fees_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_vaults_fees_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_vaults_array(owner, update_vaults_fees_factory):
    "Must revert with message 'EMPTY_VAULTS' if vaults array is empty"
    EMPTY_CALLDATA = create_calldata([], [], [], [])
    with reverts('EMPTY_VAULTS'):
        update_vaults_fees_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_array_length_mismatch(owner, stranger, update_vaults_fees_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    # Different lengths for infra fees
    CALLDATA1 = create_calldata([stranger.address], [1000, 2000], [1000], [1000])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA1)

    # Different lengths for liquidity fees
    CALLDATA2 = create_calldata([stranger.address], [1000], [1000, 2000], [1000])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA2)

    # Different lengths for reservation fees
    CALLDATA3 = create_calldata([stranger.address], [1000], [1000], [1000, 2000])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA3)

def test_zero_vault_address(owner, stranger, update_vaults_fees_factory):
    "Must revert with message 'ZERO_VAULT' if any vault is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [1000, 1000], [1000, 1000], [1000, 1000])
    with reverts('ZERO_VAULT'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA)

def test_fees_exceed_100_percent(owner, stranger, update_vaults_fees_factory, vault_hub_stub):
    "Must revert if any fee exceeds 100%"
    # Register vault first
    vault_hub_stub.connectVault(stranger)

    # Test infra fee exceeds 100%
    CALLDATA1 = create_calldata([stranger.address], [70001], [1000], [1000])
    with reverts('INFRA_FEE_TOO_HIGH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA1)

    # Test liquidity fee exceeds 100%
    CALLDATA2 = create_calldata([stranger.address], [1000], [70001], [1000])
    with reverts('LIQUIDITY_FEE_TOO_HIGH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA2)

    # Test reservation fee exceeds 100%
    CALLDATA3 = create_calldata([stranger.address], [1000], [1000], [70001])
    with reverts('RESERVATION_FEE_TOO_HIGH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA3)

def test_create_evm_script_single_vault(owner, stranger, update_vaults_fees_factory, vault_hub_stub, adapter):
    "Must create correct EVMScript for a single vault if all requirements are met"
    # Register vault first
    vault_hub_stub.connectVault(stranger)

    vaults = [stranger.address]
    infra_fees = [2000]
    liquidity_fees = [3000]
    reservation_fees = [1000]

    EVM_SCRIPT_CALLDATA = create_calldata(vaults, infra_fees, liquidity_fees, reservation_fees)
    evm_script = update_vaults_fees_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual call
    expected_calls = []
    for i in range(len(vaults)):
        expected_calls.append((
            adapter.address,
            adapter.updateVaultFees.encode_input(
                vaults[i],
                infra_fees[i],
                liquidity_fees[i],
                reservation_fees[i]
            )
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_create_evm_script_multiple_vaults(owner, accounts, update_vaults_fees_factory, vault_hub_stub, adapter):
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

    # Create expected EVMScript with individual calls for each vault
    expected_calls = []
    for i in range(len(vaults)):
        expected_calls.append((
            adapter.address,
            adapter.updateVaultFees.encode_input(
                vaults[i],
                infra_fees[i],
                liquidity_fees[i],
                reservation_fees[i]
            )
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(accounts, update_vaults_fees_factory):
    "Must decode EVMScript call data correctly"
    vaults = [accounts[1].address, accounts[2].address]
    infra_fees = [2000, 1500]
    liquidity_fees = [3000, 2500]
    reservation_fees = [1000, 500]

    EVM_SCRIPT_CALLDATA = create_calldata(vaults, infra_fees, liquidity_fees, reservation_fees)
    decoded_vaults, decoded_infra_fees, decoded_liquidity_fees, decoded_reservation_fees = update_vaults_fees_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert len(decoded_vaults) == len(vaults)
    assert len(decoded_infra_fees) == len(infra_fees)
    assert len(decoded_liquidity_fees) == len(liquidity_fees)
    assert len(decoded_reservation_fees) == len(reservation_fees)

    for i in range(len(vaults)):
        assert decoded_vaults[i] == vaults[i]
        assert decoded_infra_fees[i] == infra_fees[i]
        assert decoded_liquidity_fees[i] == liquidity_fees[i]
        assert decoded_reservation_fees[i] == reservation_fees[i]

def test_can_decrease_and_increase_fees_to_tier_limits(owner, stranger, update_vaults_fees_factory, vault_hub_stub, operator_grid_stub, adapter):
    "Must allow decreasing fees and then increasing them back to tier limits"
    vault = stranger.address

    # Register vault first
    vault_hub_stub.connectVault(vault)

    # Create a custom tier with higher fee limits
    node_operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(node_operator, 10000, {"from": owner})

    # Tier with fees: infra=5000, liquidity=4000, reservation=3000 (in basis points)
    tier_params = (10000, 200, 100, 5000, 4000, 3000)
    operator_grid_stub.registerTiers(node_operator, [tier_params], {"from": owner})

    # Set vault to use tier 1 (the newly created tier)
    operator_grid_stub.setVaultTier(vault, 1, {"from": owner})

    # Step 1: Decrease fees below tier limits - should succeed
    lower_infra_fee = 2000      # lower than tier limit of 5000
    lower_liquidity_fee = 1500  # lower than tier limit of 4000
    lower_reservation_fee = 1000 # lower than tier limit of 3000

    tx1 = adapter.updateVaultFees(vault, lower_infra_fee, lower_liquidity_fee, lower_reservation_fee, {"from": owner})
    # Should not emit VaultFeesUpdateFailed event
    assert "VaultFeesUpdateFailed" not in tx1.events

    # Step 2: Increase fees back to tier limits - should succeed (this is the new behavior)
    tier_infra_fee = 5000       # exactly at tier limit
    tier_liquidity_fee = 4000   # exactly at tier limit
    tier_reservation_fee = 3000 # exactly at tier limit

    tx2 = adapter.updateVaultFees(vault, tier_infra_fee, tier_liquidity_fee, tier_reservation_fee, {"from": owner})
    # Should not emit VaultFeesUpdateFailed event
    assert "VaultFeesUpdateFailed" not in tx2.events

    # Step 3: Try to exceed tier limits - should fail
    over_tier_infra_fee = 5001  # exceeds tier limit of 5000

    tx3 = adapter.updateVaultFees(vault, over_tier_infra_fee, tier_liquidity_fee, tier_reservation_fee, {"from": owner})
    # Should emit VaultFeesUpdateFailed event
    assert "VaultFeesUpdateFailed" in tx3.events
    assert tx3.events["VaultFeesUpdateFailed"]["vault"] == vault
    assert tx3.events["VaultFeesUpdateFailed"]["infraFeeBP"] == over_tier_infra_fee
