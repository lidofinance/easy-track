from brownie import reverts
from eth_abi import encode
from utils.evm_script import encode_call_script
from utils.hardhat_helpers import get_last_tx_revert_reason

import constants


def test_deploy(owner, easy_track, calls_script, EVMScriptExecutor):
    "Must deploy contract with correct data"
    contract = owner.deploy(EVMScriptExecutor, calls_script, easy_track)

    # validate that contract was initialized correctly
    assert contract.callsScript() == calls_script
    assert contract.easyTrack() == easy_track


def test_deploy_calls_script_not_contract(owner, accounts, easy_track, EVMScriptExecutor):
    "Must revert with message 'CALLS_SCRIPT_IS_NOT_CONTRACT'"
    not_contract = accounts[6]
    revert_reason = "CALLS_SCRIPT_IS_NOT_CONTRACT"

    try:
        with reverts(revert_reason):
            owner.deploy(EVMScriptExecutor, not_contract.address, easy_track.address)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e


def test_deploy_easy_track_not_contract(owner, accounts, calls_script, EVMScriptExecutor):
    "Must revert with message 'EASY_TRACK_IS_NOT_CONTRACT'"
    not_contract = accounts[6]
    revert_reason = "EASY_TRACK_IS_NOT_CONTRACT"

    try:
        with reverts(revert_reason):
            owner.deploy(EVMScriptExecutor, calls_script, not_contract)
    except Exception as e:
        if revert_reason != get_last_tx_revert_reason():
            raise e


def test_execute_evm_script_revert_msg(
    easy_track,
    node_operator,
    evm_script_executor,
    increase_node_operator_staking_limit,
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
                            "0x" + encode(["uint256", "uint256"], [1, 500]).hex(),
                        ),
                    )
                ]
            ),
            {"from": easy_track},
        )


def test_execute_evm_script_output(easy_track, evm_script_executor, node_operators_registry_stub):
    "Must return empty bytes and emit ScriptExecuted(_caller, _evmScript) event"
    assert node_operators_registry_stub.stakingLimit() == 200
    evm_script = encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(1, 500),
            )
        ]
    )

    # validate return value
    assert evm_script_executor.executeEVMScript.call(evm_script, {"from": easy_track}) == "0x"

    tx = evm_script_executor.executeEVMScript(evm_script, {"from": easy_track})

    # validate events
    assert tx.events["ScriptExecuted"]["_caller"] == easy_track
    assert tx.events["ScriptExecuted"]["_evmScript"] == evm_script
    assert node_operators_registry_stub.stakingLimit() == 500


def test_execute_evm_script_caller_validation(stranger, easy_track, evm_script_executor, node_operators_registry_stub):
    "Must accept calls to executeEVMScript only from EasyTrack contracts"
    with reverts("CALLER_IS_FORBIDDEN"):
        evm_script_executor.executeEVMScript("0x", {"from": stranger})

    evm_script = encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(1, 500),
            )
        ]
    )

    # must execute scripts when called by Voting or EasyTrack
    evm_script_executor.executeEVMScript(evm_script, {"from": easy_track})


def test_set_easy_track_called_by_stranger(accounts, stranger, evm_script_executor):
    "Must revert with message 'Ownable: caller is not the owner'"
    new_easy_track = accounts[4]
    with reverts("Ownable: caller is not the owner"):
        evm_script_executor.setEasyTrack(new_easy_track, {"from": stranger})


def test_set_easy_track_called_by_owner(accounts, owner, ldo, voting, evm_script_executor, easy_track, EasyTrack):
    "Must set new easyTrack value and emit EasyTrackChanged(address _previousEasyTrack, address _newEasyTrack) event"
    assert evm_script_executor.easyTrack() == easy_track

    new_easy_track = owner.deploy(
        EasyTrack,
        ldo,
        voting,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )
    tx = evm_script_executor.setEasyTrack(new_easy_track, {"from": owner})
    assert evm_script_executor.easyTrack() == new_easy_track

    # validate events
    assert len(tx.events) == 1
    assert tx.events["EasyTrackChanged"]["_previousEasyTrack"] == easy_track
    assert tx.events["EasyTrackChanged"]["_newEasyTrack"] == new_easy_track
