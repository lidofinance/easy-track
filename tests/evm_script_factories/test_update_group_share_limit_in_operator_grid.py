import pytest
from brownie import reverts, UpdateGroupShareLimitInOperatorGrid, ZERO_ADDRESS, OperatorGridMock # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(operator, new_share_limit):
    return encode_calldata(["address", "uint256"], [operator, new_share_limit])

@pytest.fixture(scope="module")
def operator_grid(owner):
    return OperatorGridMock.deploy(owner, {"from": owner})

@pytest.fixture(scope="module")
def update_group_share_limit_in_operator_grid_factory(owner, operator_grid):
    factory = UpdateGroupShareLimitInOperatorGrid.deploy(owner, operator_grid, {"from": owner})
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid, update_group_share_limit_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert update_group_share_limit_in_operator_grid_factory.trustedCaller() == owner
    assert update_group_share_limit_in_operator_grid_factory.operatorGrid() == operator_grid


def test_create_evm_script_called_by_stranger(stranger, update_group_share_limit_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_group_share_limit_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, update_group_share_limit_in_operator_grid_factory):
    EMPTY_CALLDATA = create_calldata(ZERO_ADDRESS, 1000)
    with reverts('ZeroNodeOperator: '):
        update_group_share_limit_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_group_not_exists(owner, stranger, update_group_share_limit_in_operator_grid_factory):
    CALLDATA = create_calldata(stranger.address, 1000)
    with reverts('GroupNotExists: '):
        update_group_share_limit_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, stranger, update_group_share_limit_in_operator_grid_factory, operator_grid):
    "Must create correct EVMScript if all requirements are met"
    operator_grid.registerGroup(stranger, 1000, {"from": owner})
    input_params = [stranger.address, 2000]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    evm_script = update_group_share_limit_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(operator_grid.address, operator_grid.updateGroupShareLimit.encode_input(input_params[0], input_params[1]))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(stranger, update_group_share_limit_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    input_params = [stranger.address, 2000]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    assert update_group_share_limit_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params