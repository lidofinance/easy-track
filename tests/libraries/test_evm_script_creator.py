import pytest
from eth_abi import encode_single
from utils.evm_script import encode_call_script
from brownie import reverts


@pytest.fixture(scope="module")
def create_method_calldata():
    def method(contract, method_name, params):
        return (contract.address, getattr(contract, method_name).encode_input(*params))

    return method


def test_create_evm_script_one_address_single_call(
    evm_script_creator_wrapper,
    node_operators_registry_stub,
    create_method_calldata,
):
    to = node_operators_registry_stub.address
    method_id = node_operators_registry_stub.setNodeOperatorStakingLimit.signature
    method_call_data = encode_set_node_operator_staking_limit_calldata(1, 300)
    expected_evm_script = encode_call_script(
        [
            create_method_calldata(
                node_operators_registry_stub, "setNodeOperatorStakingLimit", [1, 300]
            )
        ]
    )
    evm_script = evm_script_creator_wrapper.createEVMScript["address,bytes4,bytes"](
        to, method_id, method_call_data
    )

    assert evm_script == expected_evm_script


def test_create_evm_script_one_address_multiple_calls_same_method(
    node_operator,
    evm_script_creator_wrapper,
    node_operators_registry_stub,
    create_method_calldata,
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
            create_method_calldata(
                node_operators_registry_stub, "setNodeOperatorStakingLimit", [1, 300]
            ),
            create_method_calldata(
                node_operators_registry_stub, "setNodeOperatorStakingLimit", [2, 500]
            ),
            create_method_calldata(
                node_operators_registry_stub, "setNodeOperatorStakingLimit", [3, 600]
            ),
        ]
    )
    evm_script = evm_script_creator_wrapper.createEVMScript["address,bytes4,bytes[]"](
        to, method_id, method_call_data
    )

    assert evm_script == expected_evm_script


def test_create_evm_script_one_address_different_methods_different_lengths(
    evm_script_creator_wrapper, node_operators_registry_stub
):
    # _methodIds.length !== _evmScriptCallData.length
    with reverts("LENGTH_MISMATCH"):
        evm_script_creator_wrapper.createEVMScript["address,bytes4[],bytes[]"](
            node_operators_registry_stub.address,
            [
                node_operators_registry_stub.setNodeOperatorStakingLimit.signature,
            ],
            [
                encode_set_node_operator_staking_limit_calldata(1, 300),
                encode_set_node_operator_staking_limit_calldata(1, 300),
            ],
        )


def test_create_evm_script_one_address_different_methods(
    accounts,
    reward_programs_registry,
    evm_script_creator_wrapper,
    create_method_calldata,
):
    reward_program_to_add = accounts[3]
    reward_program_to_remove = accounts[4]
    new_reward_program_title = "new reward program"

    expected_evm_script = encode_call_script(
        [
            create_method_calldata(
                reward_programs_registry,
                "addRewardProgram",
                [reward_program_to_add, new_reward_program_title],
            ),
            create_method_calldata(
                reward_programs_registry,
                "removeRewardProgram",
                [reward_program_to_remove],
            ),
        ]
    )
    evm_script = evm_script_creator_wrapper.createEVMScript["address,bytes4[],bytes[]"](
        reward_programs_registry.address,
        [
            reward_programs_registry.addRewardProgram.signature,
            reward_programs_registry.removeRewardProgram.signature,
        ],
        [
            encode_add_reward_program_calldata(
                reward_program_to_add.address, new_reward_program_title
            ),
            encode_remove_reward_program_calldata(reward_program_to_remove.address),
        ],
    )

    assert evm_script == expected_evm_script


def test_create_evm_script_many_addresses_different_lengths(
    accounts,
    reward_programs_registry,
    evm_script_creator_wrapper,
    node_operators_registry_stub,
):
    # _to.length !== _methodIds.length
    with reverts("LENGTH_MISMATCH"):
        evm_script_creator_wrapper.createEVMScript["address[],bytes4[],bytes[]"](
            [node_operators_registry_stub.address],
            [
                node_operators_registry_stub.setNodeOperatorStakingLimit.signature,
                reward_programs_registry.removeRewardProgram.signature,
            ],
            [
                encode_set_node_operator_staking_limit_calldata(1, 300),
            ],
        )

    # _to.length !== _evmScriptCallData.length
    with reverts("LENGTH_MISMATCH"):
        evm_script_creator_wrapper.createEVMScript["address[],bytes4[],bytes[]"](
            [node_operators_registry_stub.address],
            [
                node_operators_registry_stub.setNodeOperatorStakingLimit.signature,
            ],
            [
                encode_set_node_operator_staking_limit_calldata(1, 300),
                encode_set_node_operator_staking_limit_calldata(1, 300),
            ],
        )


def test_create_evm_script_many_addresses(
    accounts,
    reward_programs_registry,
    evm_script_creator_wrapper,
    node_operators_registry_stub,
    create_method_calldata,
):
    reward_program = accounts[3]
    to = [
        node_operators_registry_stub.address,
        reward_programs_registry.address,
        node_operators_registry_stub.address,
    ]
    method_id = [
        node_operators_registry_stub.setNodeOperatorStakingLimit.signature,
        reward_programs_registry.removeRewardProgram.signature,
        node_operators_registry_stub.setNodeOperatorStakingLimit.signature,
    ]
    method_call_data = [
        encode_set_node_operator_staking_limit_calldata(1, 300),
        encode_remove_reward_program_calldata(reward_program.address),
        encode_set_node_operator_staking_limit_calldata(3, 600),
    ]
    expected_evm_script = encode_call_script(
        [
            create_method_calldata(
                node_operators_registry_stub, "setNodeOperatorStakingLimit", [1, 300]
            ),
            create_method_calldata(
                reward_programs_registry, "removeRewardProgram", [reward_program]
            ),
            create_method_calldata(
                node_operators_registry_stub, "setNodeOperatorStakingLimit", [3, 600]
            ),
        ]
    )
    evm_script = evm_script_creator_wrapper.createEVMScript[
        "address[],bytes4[],bytes[]"
    ](to, method_id, method_call_data)

    assert evm_script == expected_evm_script


def encode_remove_reward_program_calldata(reward_program):
    return "0x" + encode_single("(address)", [reward_program]).hex()


def encode_add_reward_program_calldata(reward_program, title):
    return "0x" + encode_single("(address,string)", [reward_program, title]).hex()


def encode_set_node_operator_staking_limit_calldata(node_operator_id, staking_limit):
    return (
        "0x"
        + encode_single("(uint256,uint256)", [node_operator_id, staking_limit]).hex()
    )
