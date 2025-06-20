import pytest
from brownie import CuratedSubmitExitRequestHashes, ZERO_ADDRESS, reverts
from utils.test_helpers import create_exit_request_hash_calldata


@pytest.fixture(scope="module")
def curated_contract(node_operator, curated_registry_stub, staking_router_stub, validator_exit_bus_oracle):
    return CuratedSubmitExitRequestHashes.deploy(
        curated_registry_stub, staking_router_stub, validator_exit_bus_oracle, {"from": node_operator.address}
    )


@pytest.fixture(scope="module")
def overflowed_node_op_id():
    return 2**40


def test_deploy(node_operator, curated_registry_stub, staking_router_stub, validator_exit_bus_oracle):
    contract = CuratedSubmitExitRequestHashes.deploy(
        curated_registry_stub, staking_router_stub, validator_exit_bus_oracle, {"from": node_operator.address}
    )
    assert contract.stakingRouter() == staking_router_stub
    assert contract.validatorsExitBusOracle() == validator_exit_bus_oracle
    assert contract.nodeOperatorsRegistry() == curated_registry_stub


def test_deploy_zero_staking_router(node_operator, curated_registry_stub, validator_exit_bus_oracle):
    contract = CuratedSubmitExitRequestHashes.deploy(
        curated_registry_stub, ZERO_ADDRESS, validator_exit_bus_oracle, {"from": node_operator.address}
    )
    assert contract.stakingRouter() == ZERO_ADDRESS


def test_deploy_zero_validator_exit_bus_oracle(node_operator, curated_registry_stub, staking_router_stub):
    contract = CuratedSubmitExitRequestHashes.deploy(
        curated_registry_stub, staking_router_stub, ZERO_ADDRESS, {"from": node_operator.address}
    )
    assert contract.validatorsExitBusOracle() == ZERO_ADDRESS


def test_deploy_zero_node_operators_registry(node_operator, staking_router_stub, validator_exit_bus_oracle):
    contract = CuratedSubmitExitRequestHashes.deploy(
        ZERO_ADDRESS, staking_router_stub, validator_exit_bus_oracle, {"from": node_operator.address}
    )
    assert contract.nodeOperatorsRegistry() == ZERO_ADDRESS


def test_cannot_create_evm_script_wrong_node_operator(
    node_operator,
    curated_registry_stub,
    curated_contract,
    submit_exit_hashes_factory_config,
    exit_request_input_factory,
):
    module_id = submit_exit_hashes_factory_config["module_ids"]["curated"]
    registry = curated_registry_stub
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            registry.getNodeOperatorsCount() + 1,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR"):
        curated_contract.createEVMScript(node_operator.address, calldata, {"from": node_operator.address})


def test_cannot_create_evm_script_wrong_node_operator_multiple(
    node_operator,
    curated_registry_stub,
    curated_contract,
    submit_exit_hashes_factory_config,
    exit_request_input_factory,
):
    module_id = submit_exit_hashes_factory_config["module_ids"]["curated"]
    registry = curated_registry_stub
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            registry.getNodeOperatorsCount() + 1,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"] + 1,
            submit_exit_hashes_factory_config["pubkeys"][1],
            0,
        ),
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR"):
        curated_contract.createEVMScript(node_operator.address, calldata, {"from": node_operator.address})


def test_cannot_create_evm_script_with_node_operator_id_overflow(
    node_operator,
    submit_exit_hashes_factory_config,
    curated_contract,
    exit_request_input_factory,
    curated_registry_stub,
    overflowed_node_op_id,
):
    curated_registry_stub.setDesiredNodeOperatorCount(overflowed_node_op_id)
    module_id = submit_exit_hashes_factory_config["module_ids"]["curated"]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            overflowed_node_op_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR"):
        curated_contract.createEVMScript(node_operator.address, calldata, {"from": node_operator.address})


def test_only_node_operator_can_call_create_evm_script_wrong_caller(
    curated_contract,
    submit_exit_hashes_factory_config,
    exit_request_input_factory,
    stranger,
):
    module_id = submit_exit_hashes_factory_config["module_ids"]["curated"]
    node_op_id = submit_exit_hashes_factory_config["node_op_id"]
    exit_request_input = [
        exit_request_input_factory(
            module_id,
            node_op_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_input])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR"):
        curated_contract.createEVMScript(stranger, calldata, {"from": stranger})


def test_only_node_operator_can_call_create_evm_script_multiple_requests_wrong_caller(
    curated_contract,
    submit_exit_hashes_factory_config,
    exit_request_input_factory,
    node_operator,
):
    module_id = submit_exit_hashes_factory_config["module_ids"]["curated"]
    node_op_id = submit_exit_hashes_factory_config["node_op_id"]
    wrong_node_op_id = node_op_id + 1
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            wrong_node_op_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            module_id,
            wrong_node_op_id,
            submit_exit_hashes_factory_config["validator_index"] + 1,
            submit_exit_hashes_factory_config["pubkeys"][1],
            0,
        ),
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR"):
        curated_contract.createEVMScript(node_operator.address, calldata, {"from": node_operator.address})
