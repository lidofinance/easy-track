import random
import pytest

from brownie.network.state import Chain
from brownie import EVMScriptExecutor, accounts, reverts
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants


def test_deploy(owner):
    contract = owner.deploy(EVMScriptExecutor, constants.CALLS_SCRIPT, owner)
    assert contract.callsScript() == constants.CALLS_SCRIPT
    assert contract.trustedCaller() == owner


def test_execute_evm_script_revert_msg(
    easy_track, node_operator, evm_script_executor, increase_node_operator_staking_limit
):
    with reverts("NOT_ENOUGH_SIGNING_KEYS"):
        evm_script_executor.executeEVMScript(
            encode_call_script(
                [
                    (
                        increase_node_operator_staking_limit.address,
                        increase_node_operator_staking_limit.createEVMScript.encode_input(
                            node_operator,
                            "0x" + encode_single("(uint256,uint256)", [1, 500]).hex(),
                        ),
                    )
                ]
            ),
            {"from": easy_track},
        )


def test_execute_evm_script_output(
    easy_track, evm_script_executor, node_operators_registry_stub
):
    assert node_operators_registry_stub.stakingLimit() == 200
    evm_script = encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    1, 500
                ),
            )
        ]
    )
    tx = evm_script_executor.executeEVMScript(evm_script, {"from": easy_track})
    assert tx.events["ScriptExecuted"]["_caller"] == easy_track
    assert tx.events["ScriptExecuted"]["_evmScript"] == evm_script
    assert node_operators_registry_stub.stakingLimit() == 500


def test_execute_evm_script_called_by_stranger(stranger, evm_script_executor):
    with reverts("CALLER_IS_FORBIDDEN"):
        evm_script_executor.executeEVMScript("0x", {"from": stranger})
