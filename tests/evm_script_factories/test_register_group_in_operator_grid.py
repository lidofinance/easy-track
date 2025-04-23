import pytest
from brownie import reverts, RegisterGroupInOperatorGrid, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(operator, share_limit, tiers):
    return encode_calldata(["address", "uint256", "(uint256,uint256,uint256,uint256)[]"], [operator, share_limit, tiers])

@pytest.fixture(scope="module")
def register_group_in_operator_grid_factory(owner, operator_grid_stub):
    factory = RegisterGroupInOperatorGrid.deploy(owner, operator_grid_stub, {"from": owner})
    operator_grid_stub.grantRole(operator_grid_stub.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid_stub, register_group_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert register_group_in_operator_grid_factory.trustedCaller() == owner
    assert register_group_in_operator_grid_factory.operatorGrid() == operator_grid_stub


def test_create_evm_script_called_by_stranger(stranger, register_group_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        register_group_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_zero_nodeoperator_address(owner, register_group_in_operator_grid_factory):
    "Must revert with message 'ZeroNodeOperator: ' if operator is zero address"
    EMPTY_CALLDATA = create_calldata(ZERO_ADDRESS, 1000, [])
    with reverts('ZeroNodeOperator: '):
        register_group_in_operator_grid_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_group_exists(owner, stranger, register_group_in_operator_grid_factory, operator_grid_stub):
    "Must revert with message 'GroupExists: ' if group already exists"
    operator_grid_stub.registerGroup(stranger, 1000, {"from": owner})
    CALLDATA = create_calldata(stranger.address, 1000, [(1000, 200, 100, 50)])
    with reverts('GroupExists: '):
        register_group_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_empty_tiers_array(owner, register_group_in_operator_grid_factory):
    "Must revert with message 'EmptyTiersArray: ' if tiers array is empty"
    CALLDATA = create_calldata("0x0000000000000000000000000000000000000001", 1000, [])
    with reverts('EmptyTiersArray: '):
        register_group_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, stranger, register_group_in_operator_grid_factory, operator_grid_stub):
    "Must create correct EVMScript if all requirements are met"
    tiers = [(1000, 200, 100, 50)]  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, treasuryFeeBP)
    input_params = [stranger.address, 1000, tiers]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1], input_params[2])
    evm_script = register_group_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

    # Create expected EVMScript with both registerGroup and registerTiers calls
    register_group_calldata = operator_grid_stub.registerGroup.encode_input(input_params[0], input_params[1])
    register_tiers_calldata = operator_grid_stub.registerTiers.encode_input(input_params[0], input_params[2])
    
    expected_evm_script = encode_call_script([
        (operator_grid_stub.address, register_group_calldata),
        (operator_grid_stub.address, register_tiers_calldata)
    ])

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(stranger, register_group_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    tiers = [(1000, 200, 100, 50)]  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, treasuryFeeBP)
    input_params = [stranger.address, 1000, tiers]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1], input_params[2])
    decoded_params = register_group_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert decoded_params[0] == input_params[0]  # operator
    assert decoded_params[1] == input_params[1]  # shareLimit
    assert len(decoded_params[2]) == len(input_params[2])  # tiers array length
    for i in range(len(input_params[2])):
        assert decoded_params[2][i][0] == input_params[2][i][0]  # shareLimit
        assert decoded_params[2][i][1] == input_params[2][i][1]  # reserveRatioBP
        assert decoded_params[2][i][2] == input_params[2][i][2]  # forcedRebalanceThresholdBP
        assert decoded_params[2][i][3] == input_params[2][i][3]  # treasuryFeeBP
