import pytest
from eth_abi import encode_single
from brownie import reverts, SetNodeOperatorRewardAddresses, ZERO_ADDRESS

from utils.evm_script import encode_call_script

NEW_REWARD_ADDRESSES = [
    "0x0000000000000000000000000000000000000001",
    "0x0000000000000000000000000000000000000002",
]


@pytest.fixture(scope="module")
def set_node_operator_reward_addresses_factory(owner, node_operators_registry):
    return SetNodeOperatorRewardAddresses.deploy(
        owner, node_operators_registry, {"from": owner}
    )


def test_deploy(
    node_operators_registry, owner, set_node_operator_reward_addresses_factory
):
    "Must deploy contract with correct data"
    assert set_node_operator_reward_addresses_factory.trustedCaller() == owner
    assert (
        set_node_operator_reward_addresses_factory.nodeOperatorsRegistry()
        == node_operators_registry
    )


def test_create_evm_script_called_by_stranger(
    stranger, set_node_operator_reward_addresses_factory
):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALL_DATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_node_operator_reward_addresses_factory.createEVMScript(
            stranger, EVM_SCRIPT_CALL_DATA
        )


def test_empty_calldata(owner, set_node_operator_reward_addresses_factory):
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = (
            "0x"
            + encode_single(
                "((uint256,address)[])",
                [[]],
            ).hex()
        )
        set_node_operator_reward_addresses_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_non_sorted_calldata(owner, set_node_operator_reward_addresses_factory):
    "Must revert with message 'NODE_OPERATORS_IS_NOT_SORTED' when operator ids isn't sorted"

    input_params = [
        (id, new_reward_address)
        for id, new_reward_address in enumerate(NEW_REWARD_ADDRESSES)
    ]
    print(input_params)

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address)[])", [[input_params[1], input_params[0]]]
            ).hex()
        )
        set_node_operator_reward_addresses_factory.createEVMScript(
            owner, NON_SORTED_CALL_DATA
        )

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address)[])", [[input_params[0], input_params[0]]]
            ).hex()
        )
        set_node_operator_reward_addresses_factory.createEVMScript(
            owner, NON_SORTED_CALL_DATA
        )


def test_operator_id_out_of_range(
    owner, set_node_operator_reward_addresses_factory, node_operators_registry
):
    "Must revert with message 'NODE_OPERATOR_INDEX_OUT_OF_RANGE' when operator id gt operators count"

    with reverts("NODE_OPERATOR_INDEX_OUT_OF_RANGE"):
        node_operators_count = node_operators_registry.getNodeOperatorsCount()
        CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address)[])",
                [[(node_operators_count, NEW_REWARD_ADDRESSES[0])]],
            ).hex()
        )
        set_node_operator_reward_addresses_factory.createEVMScript(owner, CALL_DATA)


def test_same_reward_address(
    owner, set_node_operator_reward_addresses_factory, node_operators_registry
):
    "Must revert with message 'SAME_REWARD_ADDRESS' when address is the same"

    with reverts("SAME_REWARD_ADDRESS"):
        node_operator = node_operators_registry.getNodeOperator(0, True)
        CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address)[])", [[(0, node_operator["rewardAddress"])]]
            ).hex()
        )
        set_node_operator_reward_addresses_factory.createEVMScript(owner, CALL_DATA)


def test_zero_reward_address(owner, set_node_operator_reward_addresses_factory):
    "Must revert with message 'ZERO_REWARD_ADDRESS' when address is zero address"

    with reverts("ZERO_REWARD_ADDRESS"):
        CALL_DATA = (
            "0x" + encode_single("((uint256,address)[])", [[(0, ZERO_ADDRESS)]]).hex()
        )
        set_node_operator_reward_addresses_factory.createEVMScript(owner, CALL_DATA)


def test_lido_as_reward_address(
    owner, set_node_operator_reward_addresses_factory, steth
):
    "Must revert with message 'ZERO_REWARD_ADDRESS' when address is lido address"

    with reverts("LIDO_REWARD_ADDRESS"):
        CALL_DATA = (
            "0x" + encode_single("((uint256,address)[])", [[(0, steth.address)]]).hex()
        )
        set_node_operator_reward_addresses_factory.createEVMScript(owner, CALL_DATA)


def test_create_evm_script(
    owner,
    set_node_operator_reward_addresses_factory,
    node_operators_registry,
):
    "Must create correct EVMScript if all requirements are met"
    input_params = [
        (id, new_reward_address)
        for id, new_reward_address in enumerate(NEW_REWARD_ADDRESSES)
    ]

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,address)[])", [input_params]).hex()
    )
    evm_script = set_node_operator_reward_addresses_factory.createEVMScript(
        owner, EVM_SCRIPT_CALL_DATA
    )
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry.address,
                node_operators_registry.setNodeOperatorRewardAddress.encode_input(
                    input_param[0], input_param[1]
                ),
            )
            for input_param in input_params
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(
    node_operators_registry, set_node_operator_reward_addresses_factory
):
    "Must decode EVMScript call data correctly"
    input_params = [
        (id, new_reward_address)
        for id, new_reward_address in enumerate(NEW_REWARD_ADDRESSES)
    ]

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,address)[])", [input_params]).hex()
    )
    assert (
        set_node_operator_reward_addresses_factory.decodeEVMScriptCallData(
            EVM_SCRIPT_CALL_DATA
        )
        == input_params
    )
