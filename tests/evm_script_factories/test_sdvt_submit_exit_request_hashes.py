import pytest
from brownie import SDVTSubmitExitRequestHashes, ZERO_ADDRESS, reverts
from utils.test_helpers import create_exit_request_hash_calldata


@pytest.fixture(scope="module")
def sdvt_contract(owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle):
    return SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle, {"from": owner}
    )


@pytest.fixture(scope="module")
def overflowed_node_op_id():
    return 2**40


def test_deploy(owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.trustedCaller() == owner
    assert contract.stakingRouter() == staking_router_stub
    assert contract.validatorsExitBusOracle() == validator_exit_bus_oracle
    assert contract.nodeOperatorsRegistry() == sdvt_registry_stub


def test_deploy_zero_staking_router(owner, sdvt_registry_stub, validator_exit_bus_oracle):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, ZERO_ADDRESS, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.stakingRouter() == ZERO_ADDRESS


def test_deploy_zero_validator_exit_bus_oracle(owner, sdvt_registry_stub, staking_router_stub):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS, {"from": owner}
    )
    assert contract.validatorsExitBusOracle() == ZERO_ADDRESS


def test_deploy_zero_node_operators_registry(owner, staking_router_stub, validator_exit_bus_oracle):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, ZERO_ADDRESS, staking_router_stub, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.nodeOperatorsRegistry() == ZERO_ADDRESS


def test_cannot_create_evm_script_wrong_node_operator(
    owner,
    sdvt_registry_stub,
    sdvt_contract,
    submit_exit_hashes_factory_config,
    exit_request_input_factory,
):
    module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]
    registry = sdvt_registry_stub
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
    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        sdvt_contract.createEVMScript(owner, calldata, {"from": owner})


def test_cannot_create_evm_script_wrong_node_operator_multiple(
    owner,
    sdvt_registry_stub,
    sdvt_contract,
    submit_exit_hashes_factory_config,
    exit_request_input_factory,
):
    module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]
    registry = sdvt_registry_stub
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
    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        sdvt_contract.createEVMScript(owner, calldata, {"from": owner})


def test_cannot_create_evm_script_with_node_operator_id_overflow(
    owner,
    submit_exit_hashes_factory_config,
    sdvt_contract,
    exit_request_input_factory,
    sdvt_registry_stub,
    overflowed_node_op_id,
):
    sdvt_registry_stub.setDesiredNodeOperatorCount(overflowed_node_op_id)
    module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]
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
    with reverts("NODE_OPERATOR_ID_OVERFLOW"):
        sdvt_contract.createEVMScript(owner, calldata, {"from": owner})
