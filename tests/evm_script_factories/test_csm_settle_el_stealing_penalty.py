import pytest
from brownie import reverts, CSMSettleElStealingPenalty, web3, history # type: ignore

from utils.evm_script import encode_call_script, encode_calldata
from utils.permission_parameters import Op, Param, encode_permission_params

OPERATORS = [
    0, 1, 2
]


def create_calldata(ids):
    return encode_calldata(["uint256[]"], [ids])


@pytest.fixture(scope="module")
def csm_settle_el_stealing_penalty_factory(owner, cs_module):
    return CSMSettleElStealingPenalty.deploy(owner, cs_module, {"from": owner})


def test_deploy(owner, cs_module, csm_settle_el_stealing_penalty_factory):
    "Must deploy contract with correct data"
    assert csm_settle_el_stealing_penalty_factory.trustedCaller() == owner
    assert csm_settle_el_stealing_penalty_factory.csm() == cs_module


def test_create_evm_script_called_by_stranger(stranger, csm_settle_el_stealing_penalty_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        csm_settle_el_stealing_penalty_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, csm_settle_el_stealing_penalty_factory):
    EMPTY_CALLDATA = create_calldata([])
    with reverts('EMPTY_NODE_OPERATORS_IDS'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_operator_id_out_of_range(owner, csm_settle_el_stealing_penalty_factory, cs_module):
    "Must revert with message 'OUT_OF_RANGE_NODE_OPERATOR_ID' when operator id gt operators count"

    node_operators_count = cs_module.getNodeOperatorsCount()
    CALLDATA = create_calldata([node_operators_count])
    with reverts('OUT_OF_RANGE_NODE_OPERATOR_ID'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, csm_settle_el_stealing_penalty_factory, cs_module):
    "Must create correct EVMScript if all requirements are met"
    input_params = OPERATORS

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    evm_script = csm_settle_el_stealing_penalty_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(cs_module.address, cs_module.settleELRewardsStealingPenalty.encode_input(input_params))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(csm_settle_el_stealing_penalty_factory):
    "Must decode EVMScript call data correctly"
    input_params = OPERATORS

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    assert csm_settle_el_stealing_penalty_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params
