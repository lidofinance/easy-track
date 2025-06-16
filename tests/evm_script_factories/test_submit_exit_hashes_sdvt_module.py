import pytest
import brownie
from brownie import SDVTModuleSubmitExitRequestHashes, ZERO_ADDRESS, convert
from utils.evm_script import encode_call_script
from utils.test_helpers import create_exit_requests_hashes, create_exit_request_hash_calldata


@pytest.fixture(scope="module")
def sdvt_submit_exit_request_hashes(owner, staking_router_stub, sdvt_registry, validator_exit_bus_oracle):
    return SDVTModuleSubmitExitRequestHashes.deploy(
        owner,
        staking_router_stub,
        sdvt_registry,
        validator_exit_bus_oracle,
        {"from": owner},
    )


## ---- Deployment tests ----


def test_deploy(
    owner,
    staking_router_stub,
    sdvt_registry,
    validator_exit_bus_oracle,
    SDVTModuleSubmitExitRequestHashes,
):
    "Must deploy contract with correct data"
    contract = owner.deploy(
        SDVTModuleSubmitExitRequestHashes, owner, staking_router_stub, sdvt_registry, validator_exit_bus_oracle
    )

    assert contract.trustedCaller() == owner
    assert contract.stakingRouter() == staking_router_stub
    assert contract.validatorsExitBusOracle() == validator_exit_bus_oracle
    assert contract.sdvtNodeOperatorsRegistry() == sdvt_registry


def test_deploy_zero_staking_router_stub(
    owner,
    sdvt_registry,
    validator_exit_bus_oracle,
):
    "Must deploy contract with zero staking router"
    contract = SDVTModuleSubmitExitRequestHashes.deploy(
        owner,
        ZERO_ADDRESS,
        sdvt_registry,
        validator_exit_bus_oracle,
        {"from": owner},
    )
    assert contract.stakingRouter() == ZERO_ADDRESS


def test_deploy_zero_validator_exit_bus_oracle(
    owner,
    staking_router_stub,
    sdvt_registry,
):
    "Must deploy contract with zero validator exit bus oracle"
    contract = SDVTModuleSubmitExitRequestHashes.deploy(
        owner, staking_router_stub, sdvt_registry, ZERO_ADDRESS, {"from": owner}
    )
    assert contract.validatorsExitBusOracle() == ZERO_ADDRESS


def test_deploy_zero_node_operators_registry(
    owner,
    staking_router_stub,
    validator_exit_bus_oracle,
):
    "Must deploy contract with zero node operators registry"
    contract = SDVTModuleSubmitExitRequestHashes.deploy(
        owner, staking_router_stub, ZERO_ADDRESS, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.sdvtNodeOperatorsRegistry() == ZERO_ADDRESS


## ---- EVM Script Calldata decoding ----


def test_decode_calldata(
    sdvt_submit_exit_request_hashes, submit_exit_hashes_factory_config, exit_request_input_factory
):
    "Must decode calldata correctly"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"] + 1,
            submit_exit_hashes_factory_config["validator_index"] + 1,
            submit_exit_hashes_factory_config["pubkeys"][1],
            0,
        ),
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    decoded_data = sdvt_submit_exit_request_hashes.decodeEVMScriptCallData(calldata)
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


def test_decode_calldata_empty(sdvt_submit_exit_request_hashes):
    "Must revert decoding empty calldata"
    with brownie.reverts():
        sdvt_submit_exit_request_hashes.decodeEVMScriptCallData("0x")


def test_decode_calldata_is_permissionless(
    stranger,
    submit_exit_hashes_factory_config,
    sdvt_submit_exit_request_hashes,
    exit_request_input_factory,
):
    "Must allow stranger to decode calldata"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            2,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    decoded_data = sdvt_submit_exit_request_hashes.decodeEVMScriptCallData(calldata, {"from": stranger})

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


# ## ---- EVM Script Creation ----


def test_create_evm_script(
    owner,
    submit_exit_hashes_factory_config,
    validator_exit_bus_oracle,
    sdvt_submit_exit_request_hashes,
    exit_request_input_factory,
):
    "Must create correct EVM script if all requirements are met"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_input = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_input])
    evm_script = sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)

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
    sdvt_submit_exit_request_hashes,
    exit_request_input_factory,
):
    "Must create EVM script with maximum allowed exit requests"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            i,
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
        for i in range(1, submit_exit_hashes_factory_config["max_requests_per_motion"] + 1)
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])
    evm_script = sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)

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
    sdvt_registry,
    submit_exit_hashes_factory_config,
    validator_exit_bus_oracle,
    sdvt_submit_exit_request_hashes,
    exit_request_input_factory,
):
    "Must create EVM script with latest node operator ID"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    # Use the latest node operator ID from the config
    latest_node_operator_id = sdvt_registry.getNodeOperatorsCount() - 1

    exit_request_input = [
        exit_request_input_factory(
            sdvt_module_id,
            latest_node_operator_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_input])
    evm_script = sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)

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
    owner, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if exit requests exceed maximum allowed"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            i,
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )
        for i in range(1, submit_exit_hashes_factory_config["max_requests_per_motion"] + 2)
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("MAX_REQUESTS_PER_MOTION_EXCEEDED"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_no_exit_requests(owner, sdvt_submit_exit_request_hashes):
    "Must revert if no exit requests are provided"
    calldata = create_exit_request_hash_calldata([])

    with brownie.reverts("EMPTY_REQUESTS_LIST"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_staking_module(
    owner, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if the staking module is not SDVT"
    wrong_module_id = submit_exit_hashes_factory_config["module_ids"]["curated"]

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

    with brownie.reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_staking_module_multiple(
    owner, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if the staking module is not SDVT for multiple requests"
    wrong_module_id = submit_exit_hashes_factory_config["module_ids"]["curated"]

    node_op_id = submit_exit_hashes_factory_config["node_op_id"]
    # Create multiple exit requests with one of them having a wrong module ID
    exit_request_inputs = [
        exit_request_input_factory(
            submit_exit_hashes_factory_config["module_ids"]["sdvt"],
            node_op_id,
            4,
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        # sandwich the wrong module ID request between valid ones
        exit_request_input_factory(
            wrong_module_id,
            node_op_id,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            submit_exit_hashes_factory_config["module_ids"]["sdvt"],
            node_op_id,
            5,
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_node_operator(
    owner, sdvt_registry, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if the node operator ID is not valid"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            sdvt_registry.getNodeOperatorsCount() + 1,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        )  # Invalid node operator ID
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_wrong_node_operator_multiple(
    owner, sdvt_registry, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if one of the node operator IDs is not valid in multiple requests"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            1,
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
        exit_request_input_factory(
            sdvt_module_id,
            sdvt_registry.getNodeOperatorsCount() + 1,  # Invalid node operator ID
            submit_exit_hashes_factory_config["validator_index"],
            submit_exit_hashes_factory_config["pubkeys"][0],
            0,
        ),
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_empty_pubkey(
    owner, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if the validator public key is empty"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            b"",
            0,
        )
    ]  # Empty pubkey

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("PUBKEY_IS_EMPTY"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_pubkey_too_short(
    owner, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if the validator public key is too short"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    valid_length = len(submit_exit_hashes_factory_config["pubkeys"][0])
    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            bytes.fromhex("aa" * (valid_length - 1)),
            0,
        )
    ]  # Invalid pubkey

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("INVALID_PUBKEY_LENGTH"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_pubkey_too_long(
    owner, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if the validator public key is too long"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    valid_length = len(submit_exit_hashes_factory_config["pubkeys"][0])
    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            bytes.fromhex("aa" * (valid_length + 1)),
            0,
        )
    ]  # Invalid pubkey

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("INVALID_PUBKEY_LENGTH"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)


def test_cannot_create_evm_script_with_wrong_pubkey(
    owner, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes, exit_request_input_factory
):
    "Must revert if the validator public key is not in the allowed list"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    # Use a pubkey that is not in the allowed list
    invalid_pubkey = submit_exit_hashes_factory_config["pubkeys"][1]  # 48-byte hex string

    exit_request_inputs = [
        exit_request_input_factory(
            sdvt_module_id,
            submit_exit_hashes_factory_config["node_op_id"],
            submit_exit_hashes_factory_config["validator_index"],
            invalid_pubkey,
            0,
        )
    ]

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_request_inputs])

    with brownie.reverts("INVALID_PUBKEY"):
        sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)
