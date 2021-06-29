import random
import pytest

from brownie.network.state import Chain
from brownie import (
    Contract,
    ContractProxy,
    EVMScriptExecutor,
    accounts,
    reverts,
    ZERO_ADDRESS,
)
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants


def test_deploy(owner, easy_track):
    # deploy contract and proxy
    contract = owner.deploy(EVMScriptExecutor)
    proxy = owner.deploy(
        ContractProxy,
        contract,
        contract.__EVMScriptExecutor_init.encode_input(
            constants.CALLS_SCRIPT, easy_track
        ),
    )

    # validate that proxy has correct implementation
    assert proxy.implementation() == contract

    proxied_contract = Contract.from_abi(
        "EVMScriptExecutorProxied", proxy, EVMScriptExecutor.abi
    )
    # validate that contract was initialized
    assert proxied_contract.owner() == owner
    assert proxied_contract.callsScript() == constants.CALLS_SCRIPT
    assert proxied_contract.trustedCaller() == easy_track


def test_upgrade_to_called_by_stranger(stranger, evm_script_executor):
    with reverts("Ownable: caller is not the owner"):
        evm_script_executor.upgradeToAndCall(ZERO_ADDRESS, "", {"from": stranger})


def test_upgrade_to(owner, easy_track, evm_script_executor):
    new_logic = owner.deploy(EVMScriptExecutor)
    evm_script_executor.upgradeTo(new_logic, {"from": owner})
    proxy = Contract.from_abi("Proxy", evm_script_executor, ContractProxy.abi)
    assert proxy.implementation() == new_logic


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
