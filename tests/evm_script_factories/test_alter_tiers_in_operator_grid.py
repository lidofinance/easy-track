import pytest
from brownie import reverts, AlterTiersInOperatorGrid # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(tier_ids, tier_params):
    return encode_calldata(["uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[]"], [tier_ids, tier_params])

@pytest.fixture(scope="module")
def alter_tiers_in_operator_grid_factory(owner, operator_grid_stub):
    factory = AlterTiersInOperatorGrid.deploy(owner, operator_grid_stub, {"from": owner})
    operator_grid_stub.grantRole(operator_grid_stub.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid_stub, alter_tiers_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert alter_tiers_in_operator_grid_factory.trustedCaller() == owner
    assert alter_tiers_in_operator_grid_factory.operatorGrid() == operator_grid_stub


def test_create_evm_script_called_by_stranger(stranger, alter_tiers_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        alter_tiers_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_tier_ids_array(owner, alter_tiers_in_operator_grid_factory):
    "Must revert with message 'Empty tier IDs array' if tier IDs array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('Empty tier IDs array'):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_array_length_mismatch(owner, alter_tiers_in_operator_grid_factory):
    "Must revert with message 'Array length mismatch' if arrays have different lengths"
    tier_params = [(1000, 200, 100, 50, 40, 10)]
    CALLDATA = create_calldata([0, 1], tier_params)
    with reverts('Array length mismatch'):
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


def test_create_evm_script(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must create correct EVMScript if all requirements are met"

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


def test_zero_reserve_ratio(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Zero reserve ratio' if reserve ratio is zero"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 0, 100, 50, 40, 10)]  # reserveRatioBP = 0
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Zero reserve ratio"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_reserve_ratio_too_high(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Reserve ratio too high' if reserve ratio exceeds 100%"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 70001, 100, 50, 40, 10)]  # reserveRatioBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Reserve ratio too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_zero_forced_rebalance_threshold(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Zero forced rebalance threshold' if forced rebalance threshold is zero"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 0, 50, 40, 10)]  # forcedRebalanceThresholdBP = 0
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Zero forced rebalance threshold"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_too_high(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Forced rebalance threshold too high' if forced rebalance threshold exceeds reserve ratio"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 300, 50, 40, 10)]  # forcedRebalanceThresholdBP > reserveRatioBP
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Forced rebalance threshold too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_infra_fee_too_high(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Infra fee too high' if infra fee exceeds 100%"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 100, 70001, 40, 10)]  # infraFeeBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Infra fee too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_liquidity_fee_too_high(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Liquidity fee too high' if liquidity fee exceeds 100%"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 100, 50, 70001, 10)]  # liquidityFeeBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Liquidity fee too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_reservation_fee_too_high(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Reservation fee too high' if reservation fee exceeds 100%"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(1000, 200, 100, 50, 40, 70001)]  # reservationFeeBP > uint16.max
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Reservation fee too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_fees_less_than_uint16_max(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must not revert if fees are less than uint16.max"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]

    tier_params = [(1000, 200, 100, 70001, 100, 100)]
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Infra fee too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)

    tier_params = [(1000, 200, 100, 100, 70001, 100)]
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Liquidity fee too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)

    tier_params = [(1000, 200, 100, 100, 100, 70001)]
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Reservation fee too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)
    


def test_share_limit_exceeds_group_share_limit(owner, alter_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'Tier share limit too high' if tier share limit exceeds group share limit"
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = (1000, 200, 100, 50, 40, 10)
    operator_grid_stub.registerTiers(operator_address, [initial_tier_params], {"from": owner})

    tier_ids = [1]
    tier_params = [(2000, 200, 100, 50, 40, 10)]  # shareLimit > group share limit
    CALLDATA = create_calldata(tier_ids, tier_params)
    with reverts("Tier share limit too high"):
        alter_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)
