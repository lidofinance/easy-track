import pytest
from brownie import interface, reverts, UpdateVaultsFeesInOperatorGrid, VaultsAdapter, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata
from utils.hardhat_helpers import get_last_tx_revert_reason

def create_calldata(vaults, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp):
    return encode_calldata(
        ["address[]", "uint256[]", "uint256[]", "uint256[]"],
        [vaults, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp]
    )

@pytest.fixture(scope="module")
def adapter(owner, lido_locator_stub):
    adapter = VaultsAdapter.deploy(owner, lido_locator_stub, owner, 1000000000000000000, {"from": owner})
    return adapter

@pytest.fixture(scope="module")
def update_vaults_fees_factory(owner, adapter, lido_locator_stub):
    # Deploy with max fee limits: maxLiquidityFeeBP=10000, maxReservationFeeBP=10000, maxInfraFeeBP=10000 (100%)
    factory = UpdateVaultsFeesInOperatorGrid.deploy(owner, adapter, lido_locator_stub, 10000, 10000, 10000, {"from": owner})
    return factory

def test_deploy(owner, update_vaults_fees_factory, adapter, lido_locator_stub):
    "Must deploy contract with correct data"
    assert update_vaults_fees_factory.trustedCaller() == owner
    assert update_vaults_fees_factory.vaultsAdapter() == adapter
    assert update_vaults_fees_factory.lidoLocator() == lido_locator_stub
    assert update_vaults_fees_factory.maxLiquidityFeeBP() == 10000
    assert update_vaults_fees_factory.maxReservationFeeBP() == 10000
    assert update_vaults_fees_factory.maxInfraFeeBP() == 10000
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == owner
    assert adapter.evmScriptExecutor() == owner
    assert adapter.lidoLocator() == lido_locator_stub

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
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [30, 30], [30, 30], [5, 5])
    with reverts('ZERO_VAULT'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA)

def test_fees_exceed_tier_limits(owner, stranger, update_vaults_fees_factory, lido_locator_stub):
    "Must revert if any fee exceeds tier limits"
    vault_hub_stub = interface.IVaultHub(lido_locator_stub.vaultHub())
    # Register vault first
    vault_hub_stub.connectVault(stranger, {"from": owner})

    # Default tier has limits: infra=50, liquidity=40, reservation=10 (from stub)
    # Test infra fee exceeds tier limit
    CALLDATA1 = create_calldata([stranger.address], [51], [30], [5])  # 51 > 50, others within limits
    with reverts('INFRA_FEE_TOO_HIGH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA1)

    # Test liquidity fee exceeds tier limit
    CALLDATA2 = create_calldata([stranger.address], [30], [41], [5])  # 41 > 40, others within limits
    with reverts('LIQUIDITY_FEE_TOO_HIGH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA2)

    # Test reservation fee exceeds tier limit
    CALLDATA3 = create_calldata([stranger.address], [30], [30], [11])  # 11 > 10, others within limits
    with reverts('RESERVATION_FEE_TOO_HIGH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA3)

def test_create_evm_script_single_vault(owner, stranger, update_vaults_fees_factory, lido_locator_stub, adapter):
    "Must create correct EVMScript for a single vault if all requirements are met"
    vault_hub_stub = interface.IVaultHub(lido_locator_stub.vaultHub())
    # Register vault first
    vault_hub_stub.connectVault(stranger, {"from": owner})

    vaults = [stranger.address]
    infra_fees = [20]  # within tier limit of 50
    liquidity_fees = [30]  # within tier limit of 40
    reservation_fees = [5]  # within tier limit of 10

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

def test_create_evm_script_multiple_vaults(owner, accounts, update_vaults_fees_factory, lido_locator_stub, adapter):
    "Must create correct EVMScript for multiple vaults if all requirements are met"
    vault_hub_stub = interface.IVaultHub(lido_locator_stub.vaultHub())
    # Register multiple vaults first
    vault1 = accounts[1]
    vault2 = accounts[2]
    vault_hub_stub.connectVault(vault1, {"from": owner})
    vault_hub_stub.connectVault(vault2, {"from": owner})

    vaults = [vault1.address, vault2.address]
    infra_fees = [20, 15]  # within tier limit of 50
    liquidity_fees = [30, 25]  # within tier limit of 40
    reservation_fees = [5, 8]  # within tier limit of 10

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
    infra_fees = [20, 15]  # within tier limit of 50
    liquidity_fees = [30, 25]  # within tier limit of 40
    reservation_fees = [5, 8]  # within tier limit of 10

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

def test_can_create_evm_script_with_fees_up_to_tier_limits(owner, stranger, update_vaults_fees_factory, lido_locator_stub, adapter):
    "Must allow creating EVMScript with fees up to tier limits"
    vault_hub_stub = interface.IVaultHub(lido_locator_stub.vaultHub())
    operator_grid = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    vault = stranger.address

    # Register vault first
    vault_hub_stub.connectVault(vault, {"from": owner})

    # Create a custom tier with higher fee limits
    node_operator = "0x0000000000000000000000000000000000000001"
    operator_grid.registerGroup(node_operator, 10000, {"from": owner})

    # Tier with fees: infra=5000, liquidity=4000, reservation=3000 (in basis points)
    tier_params = (10000, 200, 100, 5000, 4000, 3000)
    operator_grid.registerTiers(node_operator, [tier_params], {"from": owner})

    # Set vault to use tier 1 (the newly created tier)
    operator_grid_stub = interface.IOperatorGridStub(lido_locator_stub.operatorGrid())
    operator_grid_stub.setVaultTier(vault, 1, {"from": owner})

    # Step 1: Create EVMScript with fees at tier limits - should succeed
    tier_infra_fee = 5000       # exactly at tier limit
    tier_liquidity_fee = 4000   # exactly at tier limit
    tier_reservation_fee = 3000 # exactly at tier limit

    vaults = [vault]
    infra_fees = [tier_infra_fee]
    liquidity_fees = [tier_liquidity_fee]
    reservation_fees = [tier_reservation_fee]

    EVM_SCRIPT_CALLDATA = create_calldata(vaults, infra_fees, liquidity_fees, reservation_fees)
    evm_script = update_vaults_fees_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Should create EVMScript successfully
    expected_calls = [(
        adapter.address,
        adapter.updateVaultFees.encode_input(vault, tier_infra_fee, tier_liquidity_fee, tier_reservation_fee)
    )]
    expected_evm_script = encode_call_script(expected_calls)
    assert evm_script == expected_evm_script

    # Step 2: Try to exceed tier limits in factory - should fail
    over_tier_infra_fee = 5001  # exceeds tier limit of 5000
    CALLDATA_EXCEED = create_calldata([vault], [over_tier_infra_fee], [tier_liquidity_fee], [tier_reservation_fee])
    with reverts('INFRA_FEE_TOO_HIGH'):
        update_vaults_fees_factory.createEVMScript(owner, CALLDATA_EXCEED)

def test_deploy_with_zero_adapter(owner, lido_locator_stub):
    "Must revert with message 'ZERO_ADAPTER' if adapter is zero address"
    revert_reason = 'ZERO_ADAPTER'
    try:
        with reverts(revert_reason):
            owner.deploy(UpdateVaultsFeesInOperatorGrid, owner, ZERO_ADDRESS, lido_locator_stub, 10000, 10000, 10000)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e

def test_deploy_with_zero_lido_locator(owner, adapter):
    "Must revert with message 'ZERO_LIDO_LOCATOR' if lido locator is zero address"
    revert_reason = 'ZERO_LIDO_LOCATOR'
    try:
        with reverts(revert_reason):
            owner.deploy(UpdateVaultsFeesInOperatorGrid, owner, adapter, ZERO_ADDRESS, 10000, 10000, 10000)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e

def test_deploy_with_max_liquidity_fee_too_high(owner, adapter, lido_locator_stub):
    "Must revert with message 'LIQUIDITY_FEE_TOO_HIGH' if maxLiquidityFeeBP exceeds MAX_FEE_BP (type(uint16).max = 65535)"
    MAX_FEE_BP = 65535
    revert_reason = 'LIQUIDITY_FEE_TOO_HIGH'
    try:
        with reverts(revert_reason):
            owner.deploy(UpdateVaultsFeesInOperatorGrid, owner, adapter, lido_locator_stub, MAX_FEE_BP + 1, 10000, 10000)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e

def test_deploy_with_max_reservation_fee_too_high(owner, adapter, lido_locator_stub):
    "Must revert with message 'RESERVATION_FEE_TOO_HIGH' if maxReservationFeeBP exceeds MAX_FEE_BP (type(uint16).max = 65535)"
    MAX_FEE_BP = 65535
    revert_reason = 'RESERVATION_FEE_TOO_HIGH'
    try:
        with reverts(revert_reason):
            owner.deploy(UpdateVaultsFeesInOperatorGrid, owner, adapter, lido_locator_stub, 10000, MAX_FEE_BP + 1, 10000)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e

def test_deploy_with_max_infra_fee_too_high(owner, adapter, lido_locator_stub):
    "Must revert with message 'INFRA_FEE_TOO_HIGH' if maxInfraFeeBP exceeds MAX_FEE_BP (type(uint16).max = 65535)"
    MAX_FEE_BP = 65535
    revert_reason = 'INFRA_FEE_TOO_HIGH'
    try:
        with reverts(revert_reason):
            owner.deploy(UpdateVaultsFeesInOperatorGrid, owner, adapter, lido_locator_stub, 10000, 10000, MAX_FEE_BP + 1)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e

def test_fees_exceed_max_limits(owner, stranger, adapter, lido_locator_stub):
    "Must revert if any fee exceeds factory max limits even if within tier limits"
    # Deploy factory with lower max limits: maxLiquidityFeeBP=3000, maxReservationFeeBP=2000, maxInfraFeeBP=4000
    factory = UpdateVaultsFeesInOperatorGrid.deploy(owner, adapter, lido_locator_stub, 3000, 2000, 4000, {"from": owner})

    vault_hub_stub = interface.IVaultHub(lido_locator_stub.vaultHub())
    operator_grid = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    vault = stranger.address

    # Register vault first
    vault_hub_stub.connectVault(vault, {"from": owner})

    # Create a custom tier with higher fee limits than factory max
    node_operator = "0x0000000000000000000000000000000000000001"
    operator_grid.registerGroup(node_operator, 10000, {"from": owner})

    # Tier with fees: infra=5000, liquidity=4000, reservation=3000 (all higher than factory max)
    tier_params = (10000, 200, 100, 5000, 4000, 3000)
    operator_grid.registerTiers(node_operator, [tier_params], {"from": owner})

    # Set vault to use tier 1 (the newly created tier)
    operator_grid_stub = interface.IOperatorGridStub(lido_locator_stub.operatorGrid())
    operator_grid_stub.setVaultTier(vault, 1, {"from": owner})

    # Test infra fee exceeds factory max limit (4000) but within tier limit (5000)
    CALLDATA1 = create_calldata([vault], [4001], [2000], [1000])
    with reverts('INFRA_FEE_TOO_HIGH'):
        factory.createEVMScript(owner, CALLDATA1)

    # Test liquidity fee exceeds factory max limit (3000) but within tier limit (4000)
    CALLDATA2 = create_calldata([vault], [3000], [3001], [1000])
    with reverts('LIQUIDITY_FEE_TOO_HIGH'):
        factory.createEVMScript(owner, CALLDATA2)

    # Test reservation fee exceeds factory max limit (2000) but within tier limit (3000)
    CALLDATA3 = create_calldata([vault], [3000], [2000], [2001])
    with reverts('RESERVATION_FEE_TOO_HIGH'):
        factory.createEVMScript(owner, CALLDATA3)

    # Test fees at factory max limits - should succeed
    CALLDATA4 = create_calldata([vault], [4000], [3000], [2000])
    evm_script = factory.createEVMScript(owner, CALLDATA4)

    expected_calls = [(
        adapter.address,
        adapter.updateVaultFees.encode_input(vault, 4000, 3000, 2000)
    )]
    expected_evm_script = encode_call_script(expected_calls)
    assert evm_script == expected_evm_script
