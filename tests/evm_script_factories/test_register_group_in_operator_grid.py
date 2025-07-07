import pytest
from brownie import reverts, RegisterGroupsInOperatorGrid, ZERO_ADDRESS # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(operators, share_limits, tiers):
    return encode_calldata(["address[]", "uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"], [operators, share_limits, tiers])

@pytest.fixture(scope="module")
def register_groups_in_operator_grid_factory(owner, operator_grid_stub):
    factory = RegisterGroupsInOperatorGrid.deploy(owner, operator_grid_stub, 10000, {"from": owner})
    operator_grid_stub.grantRole(operator_grid_stub.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid_stub, register_groups_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert register_groups_in_operator_grid_factory.trustedCaller() == owner
    assert register_groups_in_operator_grid_factory.operatorGrid() == operator_grid_stub


def test_create_evm_script_called_by_stranger(stranger, register_groups_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        register_groups_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_node_operators_array(owner, register_groups_in_operator_grid_factory):
    "Must revert with message 'EMPTY_NODE_OPERATORS' if operators array is empty"
    EMPTY_CALLDATA = create_calldata([], [], [[]])
    with reverts('EMPTY_NODE_OPERATORS'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_array_length_mismatch(owner, stranger, register_groups_in_operator_grid_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [1000], [[], []])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_zero_node_operator(owner, stranger, register_groups_in_operator_grid_factory):
    "Must revert with message 'ZERO_NODE_OPERATOR' if any operator is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [1000, 2000], [[(1000, 200, 100, 50, 40, 10)], [(1000, 200, 100, 50, 40, 10)]])
    with reverts('ZERO_NODE_OPERATOR'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_default_tier_operator(owner, stranger, register_groups_in_operator_grid_factory):
    "Must revert with message 'DEFAULT_TIER_OPERATOR' if any operator is DEFAULT_TIER_OPERATOR"
    DEFAULT_TIER_OPERATOR = register_groups_in_operator_grid_factory.DEFAULT_TIER_OPERATOR()
    CALLDATA = create_calldata([DEFAULT_TIER_OPERATOR, stranger.address], [1000, 2000], [[(1000, 200, 100, 50, 40, 10)], [(1000, 200, 100, 50, 40, 10)]])
    with reverts('DEFAULT_TIER_OPERATOR'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_empty_tiers_array(owner, register_groups_in_operator_grid_factory):
    "Must revert with message 'EMPTY_TIERS' if any tiers array is empty"
    CALLDATA = create_calldata(["0x0000000000000000000000000000000000000001"], [1000], [[]])
    with reverts('EMPTY_TIERS'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_group_exists(owner, stranger, register_groups_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'GROUP_EXISTS' if any group already exists"
    operator_grid_stub.registerGroup(stranger, 1000, {"from": owner})
    CALLDATA = create_calldata([stranger.address], [1000], [[(1000, 200, 100, 50, 40, 10)]])
    with reverts('GROUP_EXISTS'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, accounts, register_groups_in_operator_grid_factory, operator_grid_stub):
    "Must create correct EVMScript if all requirements are met"
    operator1 = accounts[5]
    operator2 = accounts[6]
    
    operators = [operator1.address, operator2.address]
    share_limits = [1000, 3000]
    tiers = [
        [(1000, 200, 100, 50, 40, 10)],  # Tiers for operator1
        [(2000, 300, 150, 75, 60, 20)]   # Tiers for operator2
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(operators, share_limits, tiers)
    evm_script = register_groups_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each operator
    expected_calls = []
    for i in range(len(operators)):
        # Register group
        expected_calls.append((
            operator_grid_stub.address,
            operator_grid_stub.registerGroup.encode_input(operators[i], share_limits[i])
        ))
        # Register tiers
        expected_calls.append((
            operator_grid_stub.address,
            operator_grid_stub.registerTiers.encode_input(operators[i], tiers[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(accounts, register_groups_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    operators = [accounts[5].address, accounts[6].address]
    share_limits = [1000, 1500]
    tiers = [
        [(1000, 200, 100, 50, 40, 10)],
        [(2000, 300, 150, 75, 60, 20)]
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(operators, share_limits, tiers)
    decoded_operators, decoded_share_limits, decoded_tiers = register_groups_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert len(decoded_operators) == len(operators)
    assert len(decoded_share_limits) == len(share_limits)
    assert len(decoded_tiers) == len(tiers)
    
    for i in range(len(operators)):
        assert decoded_operators[i] == operators[i]
        assert decoded_share_limits[i] == share_limits[i]
        assert len(decoded_tiers[i]) == len(tiers[i])
        for j in range(len(tiers[i])):
            assert decoded_tiers[i][j][0] == tiers[i][j][0]  # shareLimit
            assert decoded_tiers[i][j][1] == tiers[i][j][1]  # reserveRatioBP
            assert decoded_tiers[i][j][2] == tiers[i][j][2]  # forcedRebalanceThresholdBP
            assert decoded_tiers[i][j][3] == tiers[i][j][3]  # infraFeeBP
            assert decoded_tiers[i][j][4] == tiers[i][j][4]  # liquidityFeeBP
            assert decoded_tiers[i][j][5] == tiers[i][j][5]  # reservationFeeBP


def test_tier_share_limit_too_high(owner, register_groups_in_operator_grid_factory):
    "Must revert with message 'TIER_SHARE_LIMIT_TOO_HIGH' if any tier's share limit exceeds the group's share limit"
    operator = "0x0000000000000000000000000000000000000001"
    share_limit = 1000
    tiers = [[(1500, 200, 100, 50, 40, 10)]]  # Tier share limit exceeds group share limit
    CALLDATA = create_calldata([operator], [share_limit], tiers)
    with reverts('TIER_SHARE_LIMIT_TOO_HIGH'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_group_share_limit_too_high(owner, register_groups_in_operator_grid_factory):
    "Must revert with message 'GROUP_SHARE_LIMIT_TOO_HIGH' if the group's share limit exceeds the maximum allowed"
    operator = "0x0000000000000000000000000000000000000001"
    max_sane_share_limit = register_groups_in_operator_grid_factory.maxSaneShareLimit()
    share_limit = max_sane_share_limit + 1  # Exceeds maximum allowed
    tiers = [[(1000, 200, 100, 50, 40, 10)]]
    CALLDATA = create_calldata([operator], [share_limit], tiers)
    with reverts('GROUP_SHARE_LIMIT_TOO_HIGH'):
        register_groups_in_operator_grid_factory.createEVMScript(owner, CALLDATA)
