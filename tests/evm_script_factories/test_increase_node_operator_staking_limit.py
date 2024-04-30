from brownie import reverts
from eth_abi import encode
from utils.evm_script import encode_call_script


NODE_OPERATOR_ID = 1
STAKING_LIMIT = 350
CALLDATA = encode(["uint256", "uint256"], [NODE_OPERATOR_ID, STAKING_LIMIT])


def test_deploy(owner, node_operators_registry, IncreaseNodeOperatorStakingLimit):
    "Must deploy contract with correct data"
    contract = owner.deploy(IncreaseNodeOperatorStakingLimit, node_operators_registry)
    assert contract.nodeOperatorsRegistry() == node_operators_registry


def test_create_evm_script_different_reward_address(owner, stranger, increase_node_operator_staking_limit):
    "Must revert with message 'CALLER_IS_NOT_NODE_OPERATOR'"
    "if creator address is not equal to rewardAddress of node operator"
    with reverts("CALLER_IS_NOT_NODE_OPERATOR"):
        increase_node_operator_staking_limit.createEVMScript(stranger, CALLDATA)


def test_create_evm_script_node_operator_disabled(
    node_operator, node_operators_registry_stub, increase_node_operator_staking_limit
):
    "Must revert with message: 'NODE_OPERATOR_DISABLED'"
    "if node operator with rewardAddress equals to the creator is disabled"
    node_operators_registry_stub.setActive(False)
    with reverts("NODE_OPERATOR_DISABLED"):
        increase_node_operator_staking_limit.createEVMScript(node_operator, CALLDATA)


def test_create_evm_script_new_staking_limit_too_low(
    node_operator, node_operators_registry_stub, increase_node_operator_staking_limit
):
    "Must revert with message: 'STAKING_LIMIT_TOO_LOW' if new staking limit"
    "is less or equal than current staking limit of node operator"
    node_operators_registry_stub.setStakingLimit(370)
    assert node_operators_registry_stub.stakingLimit() == 370

    with reverts("STAKING_LIMIT_TOO_LOW"):
        increase_node_operator_staking_limit.createEVMScript(node_operator, CALLDATA)


def test_create_evm_script_new_staking_limit_less_than_total_signing_keys(
    node_operator, node_operators_registry_stub, increase_node_operator_staking_limit
):
    "Must revert with message: 'NOT_ENOUGH_SIGNING_KEYS' if total amount"
    "of signing keys of node operator less than new staking limit"

    node_operators_registry_stub.setTotalSigningKeys(300)
    assert node_operators_registry_stub.totalSigningKeys() == 300

    with reverts("NOT_ENOUGH_SIGNING_KEYS"):
        increase_node_operator_staking_limit.createEVMScript(node_operator, CALLDATA)


def test_create_evm_script(node_operator, node_operators_registry_stub, increase_node_operator_staking_limit):
    "Must create correct EVMScript if all requirements are met"
    evm_script = increase_node_operator_staking_limit.createEVMScript(node_operator, CALLDATA)
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(NODE_OPERATOR_ID, STAKING_LIMIT),
            )
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(increase_node_operator_staking_limit):
    "Must decode EVMScript call data correctly"
    assert increase_node_operator_staking_limit.decodeEVMScriptCallData(CALLDATA) == [
        NODE_OPERATOR_ID,
        STAKING_LIMIT,
    ]
