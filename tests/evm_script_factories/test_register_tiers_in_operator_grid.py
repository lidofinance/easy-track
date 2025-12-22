import pytest
from brownie import interface, reverts, RegisterTiersInOperatorGrid, ZERO_ADDRESS # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(operators, tiers):
    return encode_calldata(["address[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"], [operators, tiers])

@pytest.fixture(scope="module")
def register_tiers_in_operator_grid_factory(owner, lido_locator_stub):
    factory = RegisterTiersInOperatorGrid.deploy(owner, lido_locator_stub, {"from": owner})
    return factory


def test_deploy(owner, lido_locator_stub, register_tiers_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert register_tiers_in_operator_grid_factory.trustedCaller() == owner
    assert register_tiers_in_operator_grid_factory.lidoLocator() == lido_locator_stub


def test_create_evm_script_called_by_stranger(stranger, register_tiers_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        register_tiers_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_node_operators_array(owner, register_tiers_in_operator_grid_factory):
    "Must revert with message 'EMPTY_NODE_OPERATORS' if operators array is empty"
    EMPTY_CALLDATA = create_calldata([], [[]])
    with reverts('EMPTY_NODE_OPERATORS'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_array_length_mismatch(owner, stranger, register_tiers_in_operator_grid_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [[], []])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_zero_node_operator(owner, stranger, register_tiers_in_operator_grid_factory):
    "Must revert with message 'ZERO_NODE_OPERATOR' if any operator is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [[(1000, 200, 100, 50, 40, 10)], [(1000, 200, 100, 50, 40, 10)]])
    with reverts('ZERO_NODE_OPERATOR'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_empty_tiers_array(owner, stranger, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'EMPTY_TIERS' if any tiers array is empty"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator_grid_stub.registerGroup(stranger, 1000, {"from": owner})
    CALLDATA = create_calldata([stranger.address], [[]])
    with reverts('EMPTY_TIERS'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_group_not_exists(owner, stranger, register_tiers_in_operator_grid_factory):
    "Must revert with message 'GROUP_NOT_EXISTS' if any group doesn't exist"
    tiers = [(1000, 200, 100, 50, 40, 10)]
    CALLDATA = create_calldata([stranger.address], [tiers])
    with reverts('GROUP_NOT_EXISTS'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_default_tier_operator(owner, register_tiers_in_operator_grid_factory):
    "Must revert with message 'DEFAULT_TIER_OPERATOR' when trying to register tiers for DEFAULT_TIER_OPERATOR"
    DEFAULT_TIER_OPERATOR = register_tiers_in_operator_grid_factory.DEFAULT_TIER_OPERATOR()
    tiers = [(1000, 200, 100, 50, 40, 10)]
    CALLDATA = create_calldata([DEFAULT_TIER_OPERATOR], [tiers])
    with reverts('DEFAULT_TIER_OPERATOR'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, accounts, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must create correct EVMScript if all requirements are met"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator1 = accounts[5]
    operator2 = accounts[6]

    # Register operators
    operator_grid_stub.registerGroup(operator1, 1000, {"from": owner})
    operator_grid_stub.registerGroup(operator2, 1500, {"from": owner})

    operators = [operator1.address, operator2.address]
    tiers = [
        [(1000, 200, 100, 50, 40, 10)],  # Tiers for operator1
        [(800, 300, 150, 75, 60, 20)]   # Tiers for operator2
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(operators, tiers)
    evm_script = register_tiers_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each operator
    expected_calls = []
    for i in range(len(operators)):
        expected_calls.append((
            operator_grid_stub.address,
            operator_grid_stub.registerTiers.encode_input(operators[i], tiers[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(accounts, register_tiers_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    operators = [accounts[5].address, accounts[6].address]
    tiers = [
        [(1000, 200, 100, 50, 40, 10)],
        [(2000, 300, 150, 75, 60, 20)]
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(operators, tiers)
    decoded_operators, decoded_tiers = register_tiers_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert len(decoded_operators) == len(operators)
    assert len(decoded_tiers) == len(tiers)

    for i in range(len(operators)):
        assert decoded_operators[i] == operators[i]
        assert len(decoded_tiers[i]) == len(tiers[i])
        for j in range(len(tiers[i])):
            assert decoded_tiers[i][j][0] == tiers[i][j][0]  # shareLimit
            assert decoded_tiers[i][j][1] == tiers[i][j][1]  # reserveRatioBP
            assert decoded_tiers[i][j][2] == tiers[i][j][2]  # forcedRebalanceThresholdBP
            assert decoded_tiers[i][j][3] == tiers[i][j][3]  # infraFeeBP
            assert decoded_tiers[i][j][4] == tiers[i][j][4]  # liquidityFeeBP
            assert decoded_tiers[i][j][5] == tiers[i][j][5]  # reservationFeeBP


def test_tier_share_limit_too_high(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'TIER_SHARE_LIMIT_TOO_HIGH' if any tier's share limit exceeds the group's share limit"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1500, 200, 100, 50, 40, 10)]]  # Tier share limit exceeds group share limit
    CALLDATA = create_calldata([operator], tiers)
    with reverts('TIER_SHARE_LIMIT_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_zero_reserve_ratio(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'ZERO_RESERVE_RATIO' if reserve ratio is zero"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 0, 100, 50, 40, 10)]]  # reserveRatioBP = 0
    CALLDATA = create_calldata([operator], tiers)
    with reverts('ZERO_RESERVE_RATIO'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_reserve_ratio_too_high(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'RESERVE_RATIO_TOO_HIGH' if reserve ratio exceeds max"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 10000, 100, 50, 40, 10)]]  # reserveRatioBP > 9999
    CALLDATA = create_calldata([operator], tiers)
    with reverts('RESERVE_RATIO_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_zero_forced_rebalance_threshold(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'ZERO_FORCED_REBALANCE_THRESHOLD' if forced rebalance threshold is zero"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 0, 50, 40, 10)]]  # forcedRebalanceThresholdBP = 0
    CALLDATA = create_calldata([operator], tiers)
    with reverts('ZERO_FORCED_REBALANCE_THRESHOLD'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_too_high(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'FORCED_REBALANCE_THRESHOLD_TOO_HIGH' if forced rebalance threshold exceeds reserve ratio"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 300, 50, 40, 10)]]  # forcedRebalanceThresholdBP (300) > reserveRatioBP (200)
    CALLDATA = create_calldata([operator], tiers)
    with reverts('FORCED_REBALANCE_THRESHOLD_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_equals_reserve_ratio(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'FORCED_REBALANCE_THRESHOLD_TOO_HIGH' if forced rebalance threshold equals reserve ratio"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 200, 50, 40, 10)]]  # forcedRebalanceThresholdBP (200) == reserveRatioBP (200), 200 + 10 = 210 > 200
    CALLDATA = create_calldata([operator], tiers)
    with reverts('FORCED_REBALANCE_THRESHOLD_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_within_10bp_of_reserve_ratio(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'FORCED_REBALANCE_THRESHOLD_TOO_HIGH' if forced rebalance threshold is within 10 BP of reserve ratio"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 191, 50, 40, 10)]]  # forcedRebalanceThresholdBP + 10 = 201 > reserveRatioBP (200)
    CALLDATA = create_calldata([operator], tiers)
    with reverts('FORCED_REBALANCE_THRESHOLD_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_forced_rebalance_threshold_exactly_10bp_below_reserve_ratio(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must pass if forced rebalance threshold is exactly at the boundary (reserveRatioBP - 10)"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 189, 50, 40, 10)]]  # forcedRebalanceThresholdBP + 10 = 199 < reserveRatioBP (200)
    CALLDATA = create_calldata([operator], tiers)

    # Should not revert
    evm_script = register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)
    assert len(evm_script) > 0


def test_infra_fee_too_high(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'INFRA_FEE_TOO_HIGH' if infra fee exceeds max fee"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 100, 70001, 40, 10)]]  # infraFeeBP > uint16.max
    CALLDATA = create_calldata([operator], tiers)
    with reverts('INFRA_FEE_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_liquidity_fee_too_high(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'LIQUIDITY_FEE_TOO_HIGH' if liquidity fee exceeds max fee"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 100, 50, 70001, 10)]]  # liquidityFeeBP > uint16.max
    CALLDATA = create_calldata([operator], tiers)
    with reverts('LIQUIDITY_FEE_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_reservation_fee_too_high(owner, register_tiers_in_operator_grid_factory, lido_locator_stub):
    "Must revert with message 'RESERVATION_FEE_TOO_HIGH' if reservation fee exceeds max fee"
    operator_grid_stub = interface.IOperatorGrid(lido_locator_stub.operatorGrid())
    operator = "0x0000000000000000000000000000000000000001"
    operator_grid_stub.registerGroup(operator, 1000, {"from": owner})
    tiers = [[(1000, 200, 100, 50, 40, 70001)]]  # reservationFeeBP > uint16.max
    CALLDATA = create_calldata([operator], tiers)
    with reverts('RESERVATION_FEE_TOO_HIGH'):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)
