import pytest
from brownie import reverts, AlterTierInOperatorGrid # type: ignore
from utils.evm_script import encode_call_script, encode_calldata

def create_calldata(tier_id, tier_params):
    return encode_calldata(["uint256", "(uint256,uint256,uint256,uint256)"], [tier_id, tier_params])

@pytest.fixture(scope="module")
def alter_tier_in_operator_grid_factory(owner, operator_grid_stub):
    factory = AlterTierInOperatorGrid.deploy(owner, operator_grid_stub, {"from": owner})
    operator_grid_stub.grantRole(operator_grid_stub.REGISTRY_ROLE(), factory, {"from": owner})
    return factory


def test_deploy(owner, operator_grid_stub, alter_tier_in_operator_grid_factory):
    "Must deploy contract with correct data"
    assert alter_tier_in_operator_grid_factory.trustedCaller() == owner
    assert alter_tier_in_operator_grid_factory.operatorGrid() == operator_grid_stub


def test_create_evm_script_called_by_stranger(stranger, alter_tier_in_operator_grid_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        alter_tier_in_operator_grid_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_tier_not_exists(owner, alter_tier_in_operator_grid_factory):
    "Must revert with message 'Tier not exists' if tier doesn't exist"
    tier_params = (1000, 200, 100, 50)  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, treasuryFeeBP)
    CALLDATA = create_calldata(1, tier_params)  # Using tier ID 1 which doesn't exist
    with reverts('Tier not exists'):
        alter_tier_in_operator_grid_factory.createEVMScript(owner, CALLDATA)


def test_wrong_calldata_length(owner, alter_tier_in_operator_grid_factory):
    "Must revert with message 'Wrong calldata length' if calldata length is wrong"
    with reverts("Wrong calldata length"):
        alter_tier_in_operator_grid_factory.createEVMScript(owner, "0x00")


def test_create_evm_script(owner, stranger, alter_tier_in_operator_grid_factory, operator_grid_stub):
    "Must create correct EVMScript if all requirements are met"
    new_tier_params = (2000, 300, 150, 75)
    input_params = [0, new_tier_params]  # Using tier ID 0 which is the default tier

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    evm_script = alter_tier_in_operator_grid_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(operator_grid_stub.address, operator_grid_stub.alterTier.encode_input(input_params[0], input_params[1]))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(alter_tier_in_operator_grid_factory):
    "Must decode EVMScript call data correctly"
    tier_params = (1000, 200, 100, 50)
    input_params = [0, tier_params]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params[0], input_params[1])
    decoded_params = alter_tier_in_operator_grid_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    
    assert decoded_params[0] == input_params[0]  # tierId
    assert decoded_params[1][0] == input_params[1][0]  # shareLimit
    assert decoded_params[1][1] == input_params[1][1]  # reserveRatioBP
    assert decoded_params[1][2] == input_params[1][2]  # forcedRebalanceThresholdBP
    assert decoded_params[1][3] == input_params[1][3]  # treasuryFeeBP 