import pytest
from brownie import reverts, UpdateGroupsShareLimitInOperatorGrid, ZERO_ADDRESS # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(operators, share_limits):
    return encode_calldata(["address[]", "uint256[]"], [operators, share_limits])

@pytest.fixture(scope="module")
def update_groups_share_limit_in_operator_grid_factory(owner, operator_grid_stub):
    factory = UpdateGroupsShareLimitInOperatorGrid.deploy(owner, operator_grid_stub, 10000, {"from": owner})
    operator_grid_stub.grantRole(operator_grid_stub.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid_stub, update_groups_share_limit_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert update_groups_share_limit_in_operator_grid_factory.trustedCaller() == owner
    assert update_groups_share_limit_in_operator_grid_factory.operatorGrid() == operator_grid_stub


def test_create_evm_script_called_by_stranger(stranger, update_groups_share_limit_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_groups_share_limit_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_node_operators_array(owner, update_groups_share_limit_in_operator_grid_factory):
    "Must revert with message 'EMPTY_NODE_OPERATORS' if operators array is empty"
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_NODE_OPERATORS'):
        update_groups_share_limit_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_array_length_mismatch(owner, stranger, update_groups_share_limit_in_operator_grid_factory):
    "Must revert with message 'ARRAY_LENGTH_MISMATCH' if arrays have different lengths"
    CALLDATA = create_calldata([stranger.address], [1000, 2000])
    with reverts('ARRAY_LENGTH_MISMATCH'):
        update_groups_share_limit_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_zero_node_operator(owner, stranger, update_groups_share_limit_in_operator_grid_factory):
    "Must revert with message 'ZERO_NODE_OPERATOR' if any operator is zero address"
    CALLDATA = create_calldata([ZERO_ADDRESS, stranger.address], [1000, 2000])
    with reverts('ZERO_NODE_OPERATOR'):
        update_groups_share_limit_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_group_not_exists(owner, stranger, accounts, update_groups_share_limit_in_operator_grid_factory):
    "Must revert with message 'GROUP_NOT_EXISTS' if any group doesn't exist"
    CALLDATA = create_calldata([stranger.address, accounts[5].address], [1000, 2000])
    with reverts('GROUP_NOT_EXISTS'):
        update_groups_share_limit_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_share_limit_too_high(owner, accounts, update_groups_share_limit_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'SHARE_LIMIT_TOO_HIGH' if any share limit exceeds maxSaneShareLimit"
    operator = accounts[5]
    
    # Register operator first
    operator_grid_stub.registerGroup(operator, 5000, {"from": owner})
    
    # Get maxSaneShareLimit from the factory (10000 based on deployment)
    max_sane_share_limit = update_groups_share_limit_in_operator_grid_factory.maxSaneShareLimit()
    
    # Try to set share limit higher than maxSaneShareLimit
    CALLDATA = create_calldata([operator.address], [max_sane_share_limit + 1])
    with reverts('SHARE_LIMIT_TOO_HIGH'):
        update_groups_share_limit_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, accounts, update_groups_share_limit_in_operator_grid_factory, operator_grid_stub):
    "Must create correct EVMScript if all requirements are met"
    operator1 = accounts[5]
    operator2 = accounts[6]
    
    # Register operators
    operator_grid_stub.registerGroup(operator1, 1000, {"from": owner})
    operator_grid_stub.registerGroup(operator2, 1500, {"from": owner})
    
    operators = [operator1.address, operator2.address]
    share_limits = [2000, 3000]

    EVM_SCRIPT_CALLDATA = create_calldata(operators, share_limits)
    evm_script = update_groups_share_limit_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with individual calls for each operator
    expected_calls = []
    for i in range(len(operators)):
        expected_calls.append((
            operator_grid_stub.address,
            operator_grid_stub.updateGroupShareLimit.encode_input(operators[i], share_limits[i])
        ))
    expected_evm_script = encode_call_script(expected_calls)

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(accounts, update_groups_share_limit_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    operators = [accounts[5].address, accounts[6].address]
    share_limits = [2000, 3000]

    EVM_SCRIPT_CALLDATA = create_calldata(operators, share_limits)
    decoded_operators, decoded_share_limits = update_groups_share_limit_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert len(decoded_operators) == len(operators)
    assert len(decoded_share_limits) == len(share_limits)
    
    for i in range(len(operators)):
        assert decoded_operators[i] == operators[i]
        assert decoded_share_limits[i] == share_limits[i]


def test_cannot_update_share_limit_with_wrong_calldata_length(owner, update_groups_share_limit_in_operator_grid_factory):
    "Must revert if calldata length is incorrect"
    with reverts():
        update_groups_share_limit_in_operator_grid_factory.createEVMScript(owner, "0x00")
