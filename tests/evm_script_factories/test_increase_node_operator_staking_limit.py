import random
import pytest
import hashlib

from brownie.network.state import Chain
from brownie import (
    IncreaseNodeOperatorStakingLimit,
    accounts,
    reverts,
    ZERO_ADDRESS,
    web3,
)
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants

MOTION_ID = 2
NODE_OPERATOR_ID = 1
STAKING_LIMIT = 350
CALL_DATA = call_data = encode_single(
    "(uint256,uint256)", [NODE_OPERATOR_ID, STAKING_LIMIT]
)


def test_deploy(owner, node_operators_registry):
    contract = owner.deploy(IncreaseNodeOperatorStakingLimit, node_operators_registry)

    assert contract.nodeOperatorsRegistry() == node_operators_registry


def test_create_evm_script_different_reward_address(
    owner, stranger, increase_node_operator_staking_limit
):
    with reverts("CALLER_IS_NOT_NODE_OPERATOR"):
        increase_node_operator_staking_limit.createEVMScript(stranger, CALL_DATA)


def test_create_evm_script_node_operator_disabled(
    node_operator, node_operators_registry_stub, increase_node_operator_staking_limit
):
    "Must fail with error: 'NODE_OPERATOR_DISABLED'"
    node_operators_registry_stub.setActive(False)

    with reverts("NODE_OPERATOR_DISABLED"):
        increase_node_operator_staking_limit.createEVMScript(node_operator, CALL_DATA)


def test_create_evm_script_new_staking_limit_less_than_current(
    node_operator, node_operators_registry_stub, increase_node_operator_staking_limit
):
    "Must fail with error: 'STAKING_LIMIT_TOO_LOW'"

    node_operators_registry_stub.setStakingLimit(370)
    assert node_operators_registry_stub.stakingLimit() == 370

    with reverts("STAKING_LIMIT_TOO_LOW"):
        increase_node_operator_staking_limit.createEVMScript(node_operator, CALL_DATA)


def test_create_evm_script_new_staking_limit_less_than_total_signing_keys(
    node_operator, node_operators_registry_stub, increase_node_operator_staking_limit
):
    "Must fail with error: 'NOT_ENOUGH_SIGNING_KEYS'"

    node_operators_registry_stub.setTotalSigningKeys(300)
    assert node_operators_registry_stub.totalSigningKeys() == 300

    with reverts("NOT_ENOUGH_SIGNING_KEYS"):
        increase_node_operator_staking_limit.createEVMScript(node_operator, CALL_DATA)


def test_create_evm_script(
    node_operator, node_operators_registry_stub, increase_node_operator_staking_limit
):
    "Must create correct evm script"

    evm_script = increase_node_operator_staking_limit.createEVMScript(
        node_operator, CALL_DATA
    )
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    NODE_OPERATOR_ID, STAKING_LIMIT
                ),
            )
        ]
    )

    assert evm_script == expected_evm_script
