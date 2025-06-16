from brownie import reverts
from utils.test_helpers import create_exit_requests_hashes


def test_validation_passes_on_correct_request(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a valid exit request passes validation."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    validator_exit_request_utils_wrapper.validateExitRequests(
        [request.to_tuple()],
        sdvt_registry,
        staking_router_stub,
    )


def test_validation_reverts_on_empty_requests(
    validator_exit_request_utils_wrapper,
    sdvt_registry,
    staking_router_stub,
):
    """Test that an empty exit request list reverts."""
    with reverts("EMPTY_REQUESTS_LIST"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [],
            sdvt_registry,
            staking_router_stub,
        )


def test_validation_reverts_on_wrong_staking_module(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with a wrong staking module reverts."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["curated"],  # Set it to curated
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry,  # Use the SDVT registry to validate the request, should fail
            staking_router_stub,
        )


def test_validation_reverts_on_wrong_staking_module_multiple(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with a wrong staking module reverts when multiple requests are present."""
    request1 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )
    request2 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["curated"],  # Set it to curated
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request1.to_tuple(), request2.to_tuple()],
            sdvt_registry,  # Use the SDVT registry to validate the request, should fail
            staking_router_stub,
        )


def test_validation_reverts_on_empty_pubkey(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with an empty pubkey reverts."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        b"",  # Empty pubkey
        0,
    )

    with reverts("PUBKEY_IS_EMPTY"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry,
            staking_router_stub,
        )


def test_validation_reverts_on_pubkey_too_short(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with a pubkey that is too short reverts."""

    valid_length = len(submit_exit_hashes_factory_config["pubkeys"][0])
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        bytes.fromhex("aa" * (valid_length - 1)),
        0,
    )

    with reverts("INVALID_PUBKEY_LENGTH"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry,
            staking_router_stub,
        )


def test_validation_reverts_on_pubkey_too_long(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with a pubkey that is too long reverts."""

    valid_length = len(submit_exit_hashes_factory_config["pubkeys"][0])
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        bytes.fromhex("aa" * (valid_length + 1)),
        0,
    )

    with reverts("INVALID_PUBKEY_LENGTH"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry,
            staking_router_stub,
        )


def test_validation_reverts_on_wrong_pubkey(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with a wrong pubkey reverts."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    with reverts("INVALID_PUBKEY"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry,
            staking_router_stub,
        )


def test_validation_reverts_on_wrong_node_op_id(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with a wrong node operator ID reverts."""
    last_node_op_id = sdvt_registry.getNodeOperatorsCount()
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        last_node_op_id + 1,  # Use an invalid node operator ID
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry,
            staking_router_stub,
        )


def test_validation_reverts_on_wrong_node_op_id_multiple(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry,
    staking_router_stub,
):
    """Test that a request with a wrong node operator ID reverts when multiple requests are present."""
    request1 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    last_node_op_id = sdvt_registry.getNodeOperatorsCount()
    request2 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        last_node_op_id + 1,  # Use an invalid node operator ID
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        validator_exit_request_utils_wrapper.validateExitRequests(
            [request1.to_tuple(), request2.to_tuple()],
            sdvt_registry,
            staking_router_stub,
        )


def test_hash_requests(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
):
    """Test that hashing requests returns the expected hash."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    expected_hash = create_exit_requests_hashes(
        [request],
        submit_exit_hashes_factory_config["data_format"],
    )

    actual_hash = validator_exit_request_utils_wrapper.hashExitRequests([request.to_tuple()])

    assert actual_hash == expected_hash


def test_hash_requests_multiple(
    validator_exit_request_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
):
    """Test that hashing multiple requests returns the expected hash."""
    request1 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )
    request2 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    expected_hash = create_exit_requests_hashes(
        [request1, request2],
        submit_exit_hashes_factory_config["data_format"],
    )

    actual_hash = validator_exit_request_utils_wrapper.hashExitRequests([request1.to_tuple(), request2.to_tuple()])

    assert actual_hash == expected_hash


def test_hash_requests_empty(
    validator_exit_request_utils_wrapper,
    submit_exit_hashes_factory_config,
):
    """Test that hashing an empty request list returns the expected hash."""
    expected_hash = create_exit_requests_hashes([], submit_exit_hashes_factory_config["data_format"])

    actual_hash = validator_exit_request_utils_wrapper.hashExitRequests([])

    assert actual_hash == expected_hash
