import pytest
from brownie import reverts, UpdateGroupShareLimitInOperatorGrid, ZERO_ADDRESS # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(operator, new_share_limit):
    return encode_calldata(["address", "uint256"], [operator, new_share_limit])

@pytest.fixture(scope="module")
def update_group_share_limit_in_operator_grid_factory(owner, operator_grid_stub):
    factory = UpdateGroupShareLimitInOperatorGrid.deploy(owner, operator_grid_stub, {"from": owner})
    operator_grid_stub.grantRole(operator_grid_stub.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid_stub, update_group_share_limit_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert update_group_share_limit_in_operator_grid_factory.trustedCaller() == owner
    assert update_group_share_limit_in_operator_grid_factory.operatorGrid() == operator_grid_stub


def test_create_evm_script_called_by_stranger(stranger, update_group_share_limit_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_group_share_limit_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, update_group_share_limit_in_operator_grid_factory):
    "Must revert with message 'ZeroNodeOperator: ' if operator is zero address"
    EMPTY_CALLDATA = create_calldata(ZERO_ADDRESS, 1000)
    with reverts('ZeroNodeOperator: '):
        update_group_share_limit_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_group_not_exists(owner, stranger, update_group_share_limit_in_operator_grid_factory):
    "Must revert with message 'GroupNotExists: ' if group doesn't exist"
    CALLDATA = create_calldata(stranger.address, 1000)
    with reverts('GroupNotExists: '):
        update_group_share_limit_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, stranger, update_group_share_limit_in_operator_grid_factory, operator_grid_stub):
    "Must create correct EVMScript if all requirements are met"
    operator_grid_stub.registerGroup(stranger, 1000, {"from": owner})
    input_params = [stranger.address, 2000]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    evm_script = update_group_share_limit_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(operator_grid_stub.address, operator_grid_stub.updateGroupShareLimit.encode_input(input_params[0], input_params[1]))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(stranger, update_group_share_limit_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    input_params = [stranger.address, 2000]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    assert update_group_share_limit_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params

def test_cannot_update_share_limit_with_wrong_calldata_length(owner, update_group_share_limit_in_operator_grid_factory):
    "Must revert with message 'WrongCalldataLength' if calldata length is incorrect"
    with reverts("WrongCalldataLength: 1"):
        update_group_share_limit_in_operator_grid_factory.createEVMScript(owner, "0x00")