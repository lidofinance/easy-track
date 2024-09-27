import pytest
from eth_abi import encode
from brownie import reverts, SetNodeOperatorNames

from utils.evm_script import encode_call_script


def create_calldata(data):
    return (
        "0x"
        + encode(
            ["(uint256,string)[]"],
            [data],
        ).hex()
    )


@pytest.fixture(scope="module")
def set_node_operator_name_factory(owner, node_operators_registry):
    print(node_operators_registry.getNodeOperatorsCount())
    return SetNodeOperatorNames.deploy(owner, node_operators_registry, {"from": owner})


def test_deploy(node_operators_registry, owner, set_node_operator_name_factory):
    "Must deploy contract with correct data"
    assert set_node_operator_name_factory.trustedCaller() == owner
    assert set_node_operator_name_factory.nodeOperatorsRegistry() == node_operators_registry


def test_create_evm_script_called_by_stranger(stranger, set_node_operator_name_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_node_operator_name_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, set_node_operator_name_factory):
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = create_calldata([])
        set_node_operator_name_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_non_sorted_calldata(owner, set_node_operator_name_factory):
    "Must revert with message 'NODE_OPERATORS_IS_NOT_SORTED' when operator ids isn't sorted"

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        print(12333)
        NON_SORTED_CALLDATA = create_calldata([(1, "New Name"), (0, "New Name")])
        set_node_operator_name_factory.createEVMScript(owner, NON_SORTED_CALLDATA)

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALLDATA = create_calldata([(0, "New Name"), (0, "New Name")])
        set_node_operator_name_factory.createEVMScript(owner, NON_SORTED_CALLDATA)


def test_operator_id_out_of_range(owner, set_node_operator_name_factory, node_operators_registry):
    "Must revert with message 'NODE_OPERATOR_INDEX_OUT_OF_RANGE' when operator id gt operators count"

    with reverts("NODE_OPERATOR_INDEX_OUT_OF_RANGE"):
        node_operators_count = node_operators_registry.getNodeOperatorsCount()
        CALLDATA = create_calldata([(node_operators_count, "New Name")])
        set_node_operator_name_factory.createEVMScript(owner, CALLDATA)


def test_name_invalid_length(owner, set_node_operator_name_factory, node_operators_registry):
    "Must revert with message 'WRONG_NAME_LENGTH' when name length eq to 0 or gt max length"

    with reverts("WRONG_NAME_LENGTH"):
        CALLDATA = create_calldata([(0, "")])
        set_node_operator_name_factory.createEVMScript(owner, CALLDATA)

    with reverts("WRONG_NAME_LENGTH"):
        max_length = node_operators_registry.MAX_NODE_OPERATOR_NAME_LENGTH()
        CALLDATA = create_calldata([(0, "x" * (max_length + 1))])
        set_node_operator_name_factory.createEVMScript(owner, CALLDATA)


def test_same_name(owner, set_node_operator_name_factory, node_operators_registry):
    "Must revert with message 'SAME_NAME' when name is the same"

    with reverts("SAME_NAME"):
        node_operator = node_operators_registry.getNodeOperator(0, True)
        CALLDATA = create_calldata([(0, node_operator["name"])])
        set_node_operator_name_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(
    owner,
    set_node_operator_name_factory,
    node_operators_registry,
):
    "Must create correct EVMScript if all requirements are met"
    input_params = [(0, "New name"), (1, "Another Name")]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    evm_script = set_node_operator_name_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry.address,
                node_operators_registry.setNodeOperatorName.encode_input(input_param[0], input_param[1]),
            )
            for input_param in input_params
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(node_operators_registry, set_node_operator_name_factory):
    "Must decode EVMScript call data correctly"
    input_params = [(0, "New name"), (1, "Another Name")]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    assert set_node_operator_name_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params
