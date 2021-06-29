from eth_abi import encode_single
from utils.evm_script import encode_call_script


def test_create_evm_script_single_call(
    evm_script_creator, node_operators_registry_stub
):
    to = node_operators_registry_stub.address
    method_id = node_operators_registry_stub.setNodeOperatorStakingLimit.signature
    method_call_data = encode_set_node_operator_staking_limit_calldata(1, 300)
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    1, 300
                ),
            )
        ]
    )
    evm_script = evm_script_creator.createEVMScript["address,bytes4,bytes"](
        to, method_id, method_call_data
    )

    assert evm_script == expected_evm_script


def test_create_evm_script_multiple_calls(
    node_operator, evm_script_creator, node_operators_registry_stub
):
    to = node_operators_registry_stub.address
    method_id = node_operators_registry_stub.setNodeOperatorStakingLimit.signature
    method_call_data = [
        encode_set_node_operator_staking_limit_calldata(1, 300),
        encode_set_node_operator_staking_limit_calldata(2, 500),
        encode_set_node_operator_staking_limit_calldata(3, 600),
    ]
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    1, 300
                ),
            ),
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    2, 500
                ),
            ),
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    3, 600
                ),
            ),
        ]
    )
    evm_script = evm_script_creator.createEVMScript["address,bytes4,bytes[]"](
        to, method_id, method_call_data
    )

    assert evm_script == expected_evm_script


def encode_set_node_operator_staking_limit_calldata(node_operator_id, staking_limit):
    return (
        "0x"
        + encode_single("(uint256,uint256)", [node_operator_id, staking_limit]).hex()
    )
