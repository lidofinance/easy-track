import pytest
from brownie import CuratedSubmitExitRequestHashes, SDVTSubmitExitRequestHashes, convert, reverts
from utils.evm_script import encode_call_script
from utils.submit_exit_requests_test_helpers import (
    create_exit_requests_hashes,
    create_exit_request_hash_calldata,
    make_test_bytes,
)


## This test file contains tests for the SDVT and Curated SubmitExitRequestHashes factories, parameterized to avoid copy-pasting
## as they share the same logic tested here
@pytest.fixture(
    params=[
        {
            "name": "curated",
            "ContractClass": CuratedSubmitExitRequestHashes,
            "registry_fixture": "curated_registry_stub",
            "creator_fixture": "node_operator",
            "wrong_module_id_key": "sdvt",
            "constructor_args": lambda _, registry, staking_router_stub, validators_exit_bus_oracle_stub: [
                registry,
                staking_router_stub,
                validators_exit_bus_oracle_stub,
            ],
        },
        {
            "name": "sdvt",
            "ContractClass": SDVTSubmitExitRequestHashes,
            "registry_fixture": "sdvt_registry_stub",
            "creator_fixture": "owner",
            "wrong_module_id_key": "curated",
            "constructor_args": lambda trusted_caller, registry, staking_router_stub, validators_exit_bus_oracle_stub: [
                trusted_caller,
                registry,
                staking_router_stub,
                validators_exit_bus_oracle_stub,
            ],
        },
    ],
    ids=["curated", "sdvt"],
    scope="module",
)
def module_type(request):
    return request.param


@pytest.fixture(scope="module")
def creator(module_type, node_operator, owner):
    return node_operator.address if module_type["creator_fixture"] == "node_operator" else owner


@pytest.fixture(scope="module")
def submit_exit_request_hashes(
    request,
    staking_router_stub,
    validators_exit_bus_oracle_stub,
    module_type,
    node_operator,
    owner,
):
    registry_stub = request.getfixturevalue(module_type["registry_fixture"])
    creator = node_operator.address if module_type["creator_fixture"] == "node_operator" else owner
    args = module_type["constructor_args"](creator, registry_stub, staking_router_stub, validators_exit_bus_oracle_stub)
    return module_type["ContractClass"].deploy(*args, {"from": creator})


@pytest.fixture(scope="module")
def registry(request, module_type):
    return request.getfixturevalue(module_type["registry_fixture"])


@pytest.fixture(scope="module")
def module_id(submit_exit_hashes_factory_config, module_type):
    return submit_exit_hashes_factory_config["module_ids"][module_type["name"]]


@pytest.fixture(scope="module")
def overflowed_module_id():
    return 2**24


@pytest.fixture(scope="module")
def overflowed_node_op_id():
    return 2**40


# ---- EVM Script Calldata decoding ----


def test_decode_calldata(
    submit_exit_request_hashes, submit_exit_hashes_factory_config, exit_request_input_factory, module_id
):
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
    stranger, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
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
    creator,
    submit_exit_hashes_factory_config,
    validators_exit_bus_oracle_stub,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
):
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
    evm_script = submit_exit_request_hashes.createEVMScript(creator, calldata)
    exit_request_hash = create_exit_requests_hashes(exit_request_input)
    expected_evm_script = encode_call_script(
        [
            (
                validators_exit_bus_oracle_stub.address,
                validators_exit_bus_oracle_stub.submitExitRequestsHash.encode_input(exit_request_hash),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_create_evm_script_max_requests(
    creator,
    submit_exit_hashes_factory_config,
    validators_exit_bus_oracle_stub,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
):
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            i,
            submit_exit_hashes_factory_config["pubkeys"][i],
            i,
        )
        for i in range(submit_exit_hashes_factory_config["max_requests_per_motion"])
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    evm_script = submit_exit_request_hashes.createEVMScript(creator, calldata)
    exit_request_hash = create_exit_requests_hashes(exit_request_inputs)
    expected_evm_script = encode_call_script(
        [
            (
                validators_exit_bus_oracle_stub.address,
                validators_exit_bus_oracle_stub.submitExitRequestsHash.encode_input(exit_request_hash),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_create_evm_script_with_latest_node_operator(
    creator,
    registry,
    submit_exit_hashes_factory_config,
    validators_exit_bus_oracle_stub,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
):
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
    evm_script = submit_exit_request_hashes.createEVMScript(creator, calldata)
    exit_request_hash = create_exit_requests_hashes(exit_request_input)
    expected_evm_script = encode_call_script(
        [
            (
                validators_exit_bus_oracle_stub.address,
                validators_exit_bus_oracle_stub.submitExitRequestsHash.encode_input(exit_request_hash),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_cannot_create_evm_script_exceeds_max_requests(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_no_exit_requests(creator, submit_exit_request_hashes):
    calldata = create_exit_request_hash_calldata([])
    with reverts("EMPTY_REQUESTS_LIST"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_wrong_staking_module(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_type
):
    wrong = submit_exit_hashes_factory_config["module_ids"][module_type["wrong_module_id_key"]]
    exit_request_inputs = [
        exit_request_input_factory(
            wrong,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_wrong_staking_module_multiple(
    creator,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
    module_type,
):
    node_op_id = submit_exit_hashes_factory_config["node_op_id"]
    correct = module_id
    wrong = submit_exit_hashes_factory_config["module_ids"][module_type["wrong_module_id_key"]]
    exit_request_inputs = [
        exit_request_input_factory(correct, node_op_id, 4, submit_exit_hashes_factory_config["pubkeys"][0], 0),
        exit_request_input_factory(
            wrong,
            node_op_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(correct, node_op_id, 5, submit_exit_hashes_factory_config["pubkeys"][0], 0),
    ]
    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_empty_pubkey(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
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
    with reverts("INVALID_PUBKEY_LENGTH"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_pubkey_too_short(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_pubkey_too_long(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_with_wrong_pubkey(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
    invalid_pubkey = make_test_bytes(submit_exit_hashes_factory_config["max_requests_per_motion"] + 1)
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_with_wrong_pubkey_multiple(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
    invalid_pubkey = make_test_bytes(submit_exit_hashes_factory_config["max_requests_per_motion"] + 1)
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_wrong_node_operator(
    creator,
    registry,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
):
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_wrong_node_operator_multiple(
    creator,
    registry,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
):
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_with_wrong_pubkey_index(
    creator, submit_exit_hashes_factory_config, submit_exit_request_hashes, exit_request_input_factory, module_id
):
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
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_with_module_id_overflow(
    creator,
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
    # module id in the staking router is rounded to uint24, so it will not find the overflowed module id
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_with_node_operator_id_overflow(
    creator,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    registry,
    module_id,
    overflowed_node_op_id,
):
    registry.setDesiredNodeOperatorCount(overflowed_node_op_id + 1)
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
    # node operator id in the registry is rounded to uint40, so it will not find the overflowed node operator id
    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_with_duplicate_requests(
    creator,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
):
    request = exit_request_input_factory(
        module_id,
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    ).to_tuple()

    calldata = create_exit_request_hash_calldata([request, request])
    with reverts("INVALID_EXIT_REQUESTS_SORT_ORDER"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)


def test_cannot_create_evm_script_wrong_requests_index_sort_order(
    creator,
    submit_exit_hashes_factory_config,
    submit_exit_request_hashes,
    exit_request_input_factory,
    module_id,
):
    exit_request_inputs = [
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"] + 1,  # should be less than next
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][1],
            0,
        ),
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    with reverts("INVALID_EXIT_REQUESTS_SORT_ORDER"):
        submit_exit_request_hashes.createEVMScript(creator, calldata)
