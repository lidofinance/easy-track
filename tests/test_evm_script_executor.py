import constants
from eth_abi import encode_single
from brownie import EVMScriptExecutor, reverts
from utils.evm_script import encode_call_script


def test_deploy(owner, easy_track):
    "Must deploy contract with correct data"
    contract = owner.deploy(
        EVMScriptExecutor, constants.CALLS_SCRIPT, easy_track, constants.VOTING
    )

    # validate that contract was initialized correctly
    assert contract.callsScript() == constants.CALLS_SCRIPT
    assert contract.easyTrack() == easy_track
    assert contract.voting() == constants.VOTING


def test_execute_evm_script_revert_msg(
    easy_track, node_operator, evm_script_executor, increase_node_operator_staking_limit
):
    "Must forward revert message if transaction contained in EVMScript will fail"
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
            {"from": constants.VOTING},
        )


def test_execute_evm_script_output(
    easy_track, evm_script_executor, node_operators_registry_stub
):
    "Must return empty bytes and emit ScriptExecuted(_caller, _evmScript) event"
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

    # validate return value
    assert (
        evm_script_executor.executeEVMScript.call(evm_script, {"from": easy_track})
        == "0x"
    )

    tx = evm_script_executor.executeEVMScript(evm_script, {"from": easy_track})

    # validate events
    assert tx.events["ScriptExecuted"]["_caller"] == easy_track
    assert tx.events["ScriptExecuted"]["_evmScript"] == evm_script
    assert node_operators_registry_stub.stakingLimit() == 500


def test_execute_evm_script_caller_validation(
    stranger, easy_track, evm_script_executor, node_operators_registry_stub
):
    "Must accept calls to executeEVMScript only from Voting and EasyTrack contracts"
    with reverts("CALLER_IS_FORBIDDEN"):
        evm_script_executor.executeEVMScript("0x", {"from": stranger})

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

    # must execute scripts when called by Voting or EasyTrack
    evm_script_executor.executeEVMScript(evm_script, {"from": easy_track})
    evm_script_executor.executeEVMScript(evm_script, {"from": constants.VOTING})
