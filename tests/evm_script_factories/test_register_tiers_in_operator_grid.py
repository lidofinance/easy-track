import pytest
from brownie import reverts, RegisterTiersInOperatorGrid, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(operator, tiers):
    return encode_calldata(["address", "(uint256,uint256,uint256,uint256)[]"], [operator, tiers])

@pytest.fixture(scope="module")
def register_tiers_in_operator_grid_factory(owner, operator_grid_stub):
    factory = RegisterTiersInOperatorGrid.deploy(owner, operator_grid_stub, {"from": owner})
    operator_grid_stub.grantRole(operator_grid_stub.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid_stub, register_tiers_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert register_tiers_in_operator_grid_factory.trustedCaller() == owner
    assert register_tiers_in_operator_grid_factory.operatorGrid() == operator_grid_stub


def test_create_evm_script_called_by_stranger(stranger, register_tiers_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        register_tiers_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_zero_nodeoperator_address(owner, register_tiers_in_operator_grid_factory):
    "Must revert with message 'ZeroNodeOperator: ' if operator is zero address"
    EMPTY_CALLDATA = create_calldata(ZERO_ADDRESS, [])
    with reverts('ZeroNodeOperator: '):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_empty_tiers_array(owner, stranger, register_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'EmptyTiersArray: ' if tiers array is empty"
    operator_grid_stub.registerGroup(stranger, 1000, {"from": owner})
    CALLDATA = create_calldata(stranger.address, [])
    with reverts('EmptyTiersArray: '):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_group_not_exists(owner, stranger, register_tiers_in_operator_grid_factory):
    "Must revert with message 'GroupNotExists: ' if group doesn't exist"
    tiers = [(1000, 100, 200, 300)]
    CALLDATA = create_calldata(stranger.address, tiers)
    with reverts('GroupNotExists: '):
        register_tiers_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, stranger, register_tiers_in_operator_grid_factory, operator_grid_stub):
    "Must create correct EVMScript if all requirements are met"
    operator_grid_stub.registerGroup(stranger, 1000, {"from": owner})
    tiers = [(1000, 100, 200, 300)]
    input_params = [stranger.address, tiers]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    evm_script = register_tiers_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(operator_grid_stub.address, operator_grid_stub.registerTiers.encode_input(input_params[0], input_params[1]))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(stranger, register_tiers_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    tiers = [(1000, 100, 200, 300)]
    input_params = [stranger.address, tiers]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    decoded_params = register_tiers_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert decoded_params[0] == input_params[0]
    assert len(decoded_params[1]) == len(input_params[1])
    for i in range(len(input_params[1])):
        assert decoded_params[1][i][0] == input_params[1][i][0]  # shareLimit
        assert decoded_params[1][i][1] == input_params[1][i][1]  # reserveRatioBP
        assert decoded_params[1][i][2] == input_params[1][i][2]  # rebalanceThresholdBP
        assert decoded_params[1][i][3] == input_params[1][i][3]  # treasuryFeeBP