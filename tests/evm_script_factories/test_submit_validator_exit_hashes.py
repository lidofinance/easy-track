import pytest
from brownie import (
    CuratedModuleSubmitExitRequestHashes,
    SDVTModuleSubmitExitRequestHashes,
    ZERO_ADDRESS,
    convert,
    reverts,
)
from utils.evm_script import encode_call_script
from utils.test_helpers import create_exit_requests_hashes, create_exit_request_hash_calldata


# Parametrize over both modules.
@pytest.fixture(
    params=[
        {
            "name": "curated",
            "ContractClass": CuratedModuleSubmitExitRequestHashes,
            "registry_attr": "curatedNodeOperatorsRegistry",
            "registry_fixture": "curated_registry_stub",
            "wrong_module_id_key": "sdvt",
        },
        {
            "name": "sdvt",
            "ContractClass": SDVTModuleSubmitExitRequestHashes,
            "registry_attr": "sdvtNodeOperatorsRegistry",
            "registry_fixture": "sdvt_registry_stub",
            "wrong_module_id_key": "curated",
        },
    ],
    ids=["curated", "sdvt"],
    scope="module",
)
def module_type(request):
    return request.param


@pytest.fixture(scope="module")
def submit_exit_request_hashes(owner, staking_router_stub, validator_exit_bus_oracle, module_type, request):
    registry = request.getfixturevalue(module_type["registry_fixture"])
    return module_type["ContractClass"].deploy(
        owner, staking_router_stub, registry, validator_exit_bus_oracle, {"from": owner}
    )


@pytest.fixture(scope="module")
def registry(module_type, request):
    return request.getfixturevalue(module_type["registry_fixture"])


@pytest.fixture(scope="module")
def module_id_key(module_type):
    return module_type["name"]


@pytest.fixture(scope="module")
def wrong_module_id(submit_exit_hashes_factory_config, module_type):
    return submit_exit_hashes_factory_config["module_ids"][module_type["wrong_module_id_key"]]


@pytest.fixture(scope="module")
def overflowed_module_id():
    return 2**24


@pytest.fixture(scope="module")
def overflowed_node_op_id():
    return 2**40


# ---- Deployment tests ----


def test_deploy(owner, staking_router_stub, registry, validator_exit_bus_oracle, module_type):
    contract = module_type["ContractClass"].deploy(
        owner, staking_router_stub, registry, validator_exit_bus_oracle, {"from": owner}
    )

    assert contract.trustedCaller() == owner
    assert contract.stakingRouter() == staking_router_stub
    assert contract.validatorsExitBusOracle() == validator_exit_bus_oracle
    assert getattr(contract, module_type["registry_attr"])() == registry


def test_deploy_zero_staking_router(owner, registry, validator_exit_bus_oracle, module_type):
    contract = module_type["ContractClass"].deploy(
        owner, ZERO_ADDRESS, registry, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.stakingRouter() == ZERO_ADDRESS


def test_deploy_zero_validator_exit_bus_oracle(owner, staking_router_stub, registry, module_type):
    contract = module_type["ContractClass"].deploy(owner, staking_router_stub, registry, ZERO_ADDRESS, {"from": owner})
    assert contract.validatorsExitBusOracle() == ZERO_ADDRESS


def test_deploy_zero_node_operators_registry(owner, staking_router_stub, validator_exit_bus_oracle, module_type):
    contract = module_type["ContractClass"].deploy(
        owner, staking_router_stub, ZERO_ADDRESS, validator_exit_bus_oracle, {"from": owner}
    )
    assert getattr(contract, module_type["registry_attr"])() == ZERO_ADDRESS


# ---- EVM Script Calldata decoding ----


def test_decode_calldata(
    submit_exit_request_hashes, submit_exit_hashes_factory_config, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"] + 1,
            submit_exit_hashes_factory_config["validator_index"] + 1,
            submit_exit_hashes_factory_config["pubkeys"][1],
            0,
        ),
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    decoded_data = submit_exit_request_hashes.decodeEVMScriptCallData(calldata)
    request_input_with_bytes = [
        (
            req.module_id,
            req.node_op_id,
            req.val_index,
            "0x" + convert.to_bytes(req.val_pubkey, "bytes").hex(),
            req.val_pubkey_index,
        )
        for req in exit_request_inputs
    ]
    assert decoded_data == request_input_with_bytes


def test_decode_calldata_empty(submit_exit_request_hashes):
    with reverts():
        submit_exit_request_hashes.decodeEVMScriptCallData("0x")


def test_decode_calldata_is_permissionless(
    stranger, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            2,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    decoded_data = submit_exit_request_hashes.decodeEVMScriptCallData(calldata, {"from": stranger})
    request_input_with_bytes = [
        (
            req.module_id,
            req.node_op_id,
            req.val_index,
            "0x" + convert.to_bytes(req.val_pubkey, "bytes").hex(),
            req.val_pubkey_index,
        )
        for req in exit_request_inputs
    ]
    assert decoded_data == request_input_with_bytes


# ---- EVM Script Creation ----


def test_create_evm_script(
    owner,
    submit_exit_hashes_factory_config,
    validator_exit_bus_oracle,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id_key,
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    exit_request_input = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_input])
    evm_script = submit_exit_request_hashes.createEVMScript(owner, calldata)
    exit_request_hash = create_exit_requests_hashes(exit_request_input)
    expected_evm_script = encode_call_script(
        [
            (
                validator_exit_bus_oracle.address,
                validator_exit_bus_oracle.submitExitRequestsHash.encode_input(exit_request_hash),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_create_evm_script_max_requests(
    owner,
    submit_exit_hashes_factory_config,
    validator_exit_bus_oracle,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id_key,
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            i,
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
        for i in range(1, submit_exit_hashes_factory_config["max_requests_per_motion"] + 1)
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    evm_script = submit_exit_request_hashes.createEVMScript(owner, calldata)
    exit_request_hash = create_exit_requests_hashes(exit_request_inputs)
    expected_evm_script = encode_call_script(
        [
            (
                validator_exit_bus_oracle.address,
                validator_exit_bus_oracle.submitExitRequestsHash.encode_input(exit_request_hash),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_create_evm_script_with_latest_node_operator(
    owner,
    registry,
    submit_exit_hashes_factory_config,
    validator_exit_bus_oracle,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id_key,
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    latest_node_operator_id = registry.getNodeOperatorsCount() - 1
    exit_request_input = [
        exit_request_input_factory(
            module_id,
            latest_node_operator_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_input])
    evm_script = submit_exit_request_hashes.createEVMScript(owner, calldata)
    exit_request_hash = create_exit_requests_hashes(exit_request_input)
    expected_evm_script = encode_call_script(
        [
            (
                validator_exit_bus_oracle.address,
                validator_exit_bus_oracle.submitExitRequestsHash.encode_input(exit_request_hash),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_cannot_create_evm_script_exceeds_max_requests(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            i,
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
        for i in range(1, submit_exit_hashes_factory_config["max_requests_per_motion"] + 2)
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("MAX_REQUESTS_PER_MOTION_EXCEEDED"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_no_exit_requests(owner, submit_exit_request_hashes):
    calldata = create_exit_request_hash_calldata([])
    with reverts("EMPTY_REQUESTS_LIST"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_staking_module(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, wrong_module_id
):
    exit_request_inputs = [
        exit_request_input_factory(
            wrong_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_staking_module_multiple(
    owner,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id_key,
    wrong_module_id,
):
    node_op_id = submit_exit_hashes_factory_config["node_op_id"]
    correct_module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    exit_request_inputs = [
        exit_request_input_factory(
            correct_module_id, node_op_id, 4, submit_exit_hashes_factory_config["pubkeys"][0], 0
        ),
        exit_request_input_factory(
            wrong_module_id,
            node_op_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            correct_module_id, node_op_id, 5, submit_exit_hashes_factory_config["pubkeys"][0], 0
        ),
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_node_operator(
    owner,
    registry,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id_key,
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
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
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_node_operator_multiple(
    owner,
    registry,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id_key,
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
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
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_empty_pubkey(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            b"",
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("PUBKEY_IS_EMPTY"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_pubkey_too_short(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    valid_length = len(submit_exit_hashes_factory_config["pubkeys"][0])
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            bytes.fromhex("aa" * (valid_length - 1)),
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("INVALID_PUBKEY_LENGTH"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_pubkey_too_long(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    valid_length = len(submit_exit_hashes_factory_config["pubkeys"][0])
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            bytes.fromhex("aa" * (valid_length + 1)),
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("INVALID_PUBKEY_LENGTH"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_with_wrong_pubkey(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    invalid_pubkey = submit_exit_hashes_factory_config["pubkeys"][2]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            invalid_pubkey,
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("INVALID_PUBKEY"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_with_wrong_pubkey_index(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    invalid_pubkey_index = 1
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],  # valid pubkey
            invalid_pubkey_index,  # invalid pubkey index
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("INVALID_PUBKEY"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_with_wrong_pubkey_multiple(
    owner, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id_key
):
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]
    invalid_pubkey = submit_exit_hashes_factory_config["pubkeys"][2]
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            invalid_pubkey,
            0,
        ),
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"] + 1,
            submit_exit_hashes_factory_config["validator_index"] + 1,
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("INVALID_PUBKEY"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_with_module_id_overflow(
    owner,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    staking_router_stub,
    registry,
    overflowed_module_id,
):
    staking_router_stub.setStakingModule(overflowed_module_id, registry.address)
    exit_request_inputs = [
        exit_request_input_factory(
            overflowed_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("MODULE_ID_OVERFLOW"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_with_node_operator_id_overflow(
    owner,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    registry,
    module_id_key,
    overflowed_node_op_id,
):
    registry.setDesiredNodeOperatorCount(overflowed_node_op_id)
    exit_request_inputs = [
        exit_request_input_factory(
            submit_exit_hashes_factory_config["module_ids"][module_id_key],
            overflowed_node_op_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("NODE_OPERATOR_ID_OVERFLOW"):
        submit_exit_request_hashes.createEVMScript(owner, calldata)
