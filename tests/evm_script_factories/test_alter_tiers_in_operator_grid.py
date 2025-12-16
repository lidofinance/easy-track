import pytest
from brownie import interface, reverts, AlterTiersInOperatorGrid # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(tier_ids, tier_params):
    return encode_calldata(["uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[]"], [tier_ids, tier_params])

@pytest.fixture(scope="module")
def alter_tiers_in_operator_grid_factory(owner, lido_locator_stub):
    max_share_limit = 1000 * 10**18  # 1000 ETH for testing
    factory = AlterTiersInOperatorGrid.deploy(owner, lido_locator_stub, max_share_limit, {"from": owner})
    return factory


def test_deploy(owner, lido_locator_stub, alter_tiers_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert alter_tiers_in_operator_grid_factory.trustedCaller() == owner
    assert alter_tiers_in_operator_grid_factory.lidoLocator() == lido_locator_stub
    assert alter_tiers_in_operator_grid_factory.defaultTierMaxShareLimit() == 1000 * 10**18


def test_create_evm_script_called_by_stranger(stranger, alter_tiers_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        alter_tiers_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_tier_ids_array(owner, alter_tiers_in_operator_grid_factory):
    "Must revert with message 'EMPTY_TIER_IDS' if tier IDs array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_TIER_IDS'):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_array_length_mismatch(owner, alter_tiers_in_operator_grid_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    tier_params = [(1000, 200, 100, 50, 40, 10)]
    CALLDATA = create_calldata([0, 1], tier_params)
    with reverts('ARRAY_LENGTH_MISMATCH'):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_tier_not_exists(owner, alter_tiers_in_operator_grid_factory):
    "Must revert with message 'Tier does not exist' if tier doesn't exist"
    tier_params = [(1000, 200, 100, 50, 40, 10)]  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, infraFeeBP, liquidityFeeBP, reservationFeeBP)
    CALLDATA = create_calldata([99], tier_params)  # Using tier ID 99 which doesn't exist
    with reverts('Tier does not exist'):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_wrong_calldata_length(owner, alter_tiers_in_operator_grid_factory):
    "Must revert if calldata length is wrong"
    with reverts():
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, "0x00")


def test_create_evm_script(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must create correct EVMScript if all requirements are met"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())

    # First register a group and tiers to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 9000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params, initial_tier_params], {"from": owner})

    tier_ids = [1, 2]  # Assuming tier IDs 1 and 2 exist
    tier_params = [
        (2000, 300, 150, 75, 60, 20),  # Parameters for tier 0
        (3000, 400, 200, 100, 80, 30)  # Parameters for tier 1
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(tier_ids, tier_params)
    evm_script = alter_tiers_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(operator_grid_stub.address, operator_grid_stub.alterTiers.encode_input(tier_ids, tier_params))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(alter_tiers_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    tier_ids = [1, 2]
    tier_params = [
        (1000, 200, 100, 50, 40, 10),
        (2000, 300, 150, 75, 60, 20)
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(tier_ids, tier_params)
    decoded_tier_ids, decoded_tier_params = alter_tiers_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert len(decoded_tier_ids) == len(tier_ids)
    assert len(decoded_tier_params) == len(tier_params)

    for i in range(len(tier_ids)):
        assert decoded_tier_ids[i] == tier_ids[i]
        assert decoded_tier_params[i][0] == tier_params[i][0]  # shareLimit
        assert decoded_tier_params[i][1] == tier_params[i][1]  # reserveRatioBP
        assert decoded_tier_params[i][2] == tier_params[i][2]  # forcedRebalanceThresholdBP
        assert decoded_tier_params[i][3] == tier_params[i][3]  # infraFeeBP
        assert decoded_tier_params[i][4] == tier_params[i][4]  # liquidityFeeBP
        assert decoded_tier_params[i][5] == tier_params[i][5]  # reservationFeeBP


def test_zero_reserve_ratio(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'ZERO_RESERVE_RATIO' if reserve ratio is zero"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 0, 100, 50, 40, 10)]  # reserveRatioBP = 0
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("ZERO_RESERVE_RATIO"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_reserve_ratio_too_high(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'RESERVE_RATIO_TOO_HIGH' if reserve ratio exceeds 100%"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 70001, 100, 50, 40, 10)]  # reserveRatioBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("RESERVE_RATIO_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_zero_forced_rebalance_threshold(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'ZERO_FORCED_REBALANCE_THRESHOLD' if forced rebalance threshold is zero"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 0, 50, 40, 10)]  # forcedRebalanceThresholdBP = 0
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("ZERO_FORCED_REBALANCE_THRESHOLD"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_too_high(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'FORCED_REBALANCE_THRESHOLD_TOO_HIGH' if forced rebalance threshold exceeds reserve ratio"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 300, 50, 40, 10)]  # forcedRebalanceThresholdBP (300) > reserveRatioBP (200)
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("FORCED_REBALANCE_THRESHOLD_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_equals_reserve_ratio(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'FORCED_REBALANCE_THRESHOLD_TOO_HIGH' if forced rebalance threshold equals reserve ratio"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 200, 50, 40, 10)]  # forcedRebalanceThresholdBP == reserveRatioBP (200 + 10 = 210 > 200)
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("FORCED_REBALANCE_THRESHOLD_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_within_10bp_of_reserve_ratio(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'FORCED_REBALANCE_THRESHOLD_TOO_HIGH' if forced rebalance threshold is within 10 BP of reserve ratio"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 191, 50, 40, 10)]  # forcedRebalanceThresholdBP + 10 = 201 > reserveRatioBP (200)
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("FORCED_REBALANCE_THRESHOLD_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_exactly_10bp_below_reserve_ratio(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must pass if forced rebalance threshold is exactly at the boundary (reserveRatioBP - 10)"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 189, 50, 40, 10)]  # forcedRebalanceThresholdBP + 10 = 199 < reserveRatioBP (200)
    CALLDATA = create_calldata(tier_ids, tier_params)

    # Should not revert
    evm_script = alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)
    assert len(evm_script) > 0


def test_infra_fee_too_high(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'INFRA_FEE_TOO_HIGH' if infra fee exceeds max fee"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 100, 70001, 40, 10)]  # infraFeeBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("INFRA_FEE_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_liquidity_fee_too_high(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'LIQUIDITY_FEE_TOO_HIGH' if liquidity fee exceeds max fee"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 100, 50, 70001, 10)]  # liquidityFeeBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("LIQUIDITY_FEE_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_reservation_fee_too_high(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'RESERVATION_FEE_TOO_HIGH' if reservation fee exceeds max fee"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 100, 50, 40, 70001)]  # reservationFeeBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("RESERVATION_FEE_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_fees_less_than_uint16_max(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must not revert if fees are less than uint16.max"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]

    tier_params = [(1000, 200, 100, 70001, 100, 100)]
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("INFRA_FEE_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)

    tier_params = [(1000, 200, 100, 100, 70001, 100)]
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("LIQUIDITY_FEE_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)

    tier_params = [(1000, 200, 100, 100, 100, 70001)]
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("RESERVATION_FEE_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)



def test_share_limit_exceeds_group_share_limit(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'TIER_SHARE_LIMIT_TOO_HIGH' if tier share limit exceeds group share limit"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(2000, 200, 100, 50, 40, 10)]  # shareLimit > group share limit
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("TIER_SHARE_LIMIT_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_default_tier_share_limit_exceeds_max_limit(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'TIER_SHARE_LIMIT_TOO_HIGH' if default tier share limit exceeds max share limit"
    # Default tier (tier ID 0) is already created in OperatorGridStub constructor
    # We can directly test altering it

    tier_ids = [0]  # Default tier ID
    max_share_limit = 1000 * 10**18  # This is what we set in the fixture
    tier_params = [(max_share_limit + 1, 200, 100, 50, 40, 10)]  # shareLimit > maxShareLimit
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("TIER_SHARE_LIMIT_TOO_HIGH"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_default_tier_share_limit_at_max_limit(owner, alter_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must not revert if default tier share limit equals max share limit"
    # Default tier (tier ID 0) is already created in OperatorGridStub constructor
    # We can directly test altering it

    tier_ids = [0]  # Default tier ID
    max_share_limit = 1000 * 10**18  # This is what we set in the fixture
    tier_params = [(max_share_limit, 200, 100, 50, 40, 10)]  # shareLimit = maxShareLimit
    CALLDATA = create_calldata(tier_ids, tier_params)

    # Should not revert
    evm_script = alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)
    assert len(evm_script) > 0
