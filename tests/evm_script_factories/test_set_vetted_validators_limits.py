import pytest
from eth_abi import encode
from brownie import reverts, SetVettedValidatorsLimits, web3

from utils.evm_script import encode_call_script


def create_calldata(data):
    return (
        "0x"
        + encode(
            ["(uint256,uint256)[]"],
            [data],
        ).hex()
    )


@pytest.fixture(scope="module")
def set_vetted_validators_limits_factory(owner, node_operators_registry):
    return SetVettedValidatorsLimits.deploy(owner, node_operators_registry, {"from": owner})


def test_deploy(node_operators_registry, owner, set_vetted_validators_limits_factory):
    "Must deploy contract with correct data"
    assert set_vetted_validators_limits_factory.trustedCaller() == owner
    assert set_vetted_validators_limits_factory.nodeOperatorsRegistry() == node_operators_registry


def test_create_evm_script_called_by_stranger(stranger, set_vetted_validators_limits_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_vetted_validators_limits_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, set_vetted_validators_limits_factory):
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = create_calldata([])
        set_vetted_validators_limits_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_non_sorted_calldata(owner, set_vetted_validators_limits_factory):
    "Must revert with message 'NODE_OPERATORS_IS_NOT_SORTED' when operator ids isn't sorted"

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALLDATA = create_calldata([(1, 1), (0, 2)])
        set_vetted_validators_limits_factory.createEVMScript(owner, NON_SORTED_CALLDATA)

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALLDATA = create_calldata([(0, 1), (0, 2)])
        set_vetted_validators_limits_factory.createEVMScript(owner, NON_SORTED_CALLDATA)


def test_non_active_operator_calldata(
    owner, set_vetted_validators_limits_factory, node_operators_registry, voting, acl
):
    "Must revert with message 'NODE_OPERATOR_IS_NOT_ACTIVE' when operator isn't active"
    acl.grantPermission(
        voting,
        node_operators_registry,
        web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE").hex(),
        {"from": voting},
    )

    input_params = [(0, 1), (1, 1)]
    node_operators_registry.deactivateNodeOperator(0, {"from": voting})

    with reverts("NODE_OPERATOR_IS_NOT_ACTIVE"):

        EVM_SCRIPT_CALLDATA = create_calldata(input_params)
        set_vetted_validators_limits_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


def test_operator_id_out_of_range(owner, set_vetted_validators_limits_factory, node_operators_registry):
    "Must revert with message 'NODE_OPERATOR_INDEX_OUT_OF_RANGE' when operator id gt operators count"

    with reverts("NODE_OPERATOR_INDEX_OUT_OF_RANGE"):
        node_operators_count = node_operators_registry.getNodeOperatorsCount()
        CALLDATA = create_calldata([(node_operators_count, 1)])
        set_vetted_validators_limits_factory.createEVMScript(owner, CALLDATA)


def test_revert_on_not_enough_signing_keys(owner, set_vetted_validators_limits_factory, steth):
    "Must revert with message 'NOT_ENOUGH_SIGNING_KEYS' when node operator has not enough keys"

    with reverts("NOT_ENOUGH_SIGNING_KEYS"):
        CALLDATA = create_calldata([(0, 100000)])
        set_vetted_validators_limits_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(
    owner,
    set_vetted_validators_limits_factory,
    node_operators_registry,
):
    "Must create correct EVMScript if all requirements are met"

    input_params = [(0, 1), (1, 1)]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    evm_script = set_vetted_validators_limits_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry.address,
                node_operators_registry.setNodeOperatorStakingLimit.encode_input(input_param[0], input_param[1]),
            )
            for input_param in input_params
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(node_operators_registry, set_vetted_validators_limits_factory):
    "Must decode EVMScript call data correctly"
    input_params = [(0, 1), (1, 1)]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    assert set_vetted_validators_limits_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params
