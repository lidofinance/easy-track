from brownie import reverts, ZERO_ADDRESS, accounts
from utils.submit_exit_requests_test_helpers import create_exit_requests_hashes, add_node_operator


## This test module tests the validation and hashing of exit requests
## As this is a library test, it is largely irrelevant what the actual modules (SDVT, Curated) are being used
## So we default to the Npde Operator Registry Stub (SDVT) for most tests, using the Curated Registry only for specific tests where it makes sense.
def test_validation_passes_on_correct_request(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
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

    submit_exit_request_hashes_utils_wrapper.validateExitRequests(
        [request.to_tuple()],
        sdvt_registry_stub,
        staking_router_stub,
        ZERO_ADDRESS,
    )


def test_validation_passes_on_correct_request_multiple(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    node_op_id2 = add_node_operator(
        sdvt_registry_stub,
        submit_exit_hashes_factory_config["pubkeys"][1],
    )

    """Test that multiple valid exit requests pass validation."""
    request1 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )
    request2 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        node_op_id2,  # Use a different node operator ID
        submit_exit_hashes_factory_config["validator_index"] + 1,
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    submit_exit_request_hashes_utils_wrapper.validateExitRequests(
        [request1.to_tuple(), request2.to_tuple()],
        sdvt_registry_stub,
        staking_router_stub,
        ZERO_ADDRESS,
    )


def test_validation_passes_on_valid_requests_with_creator(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    curated_registry_stub,
    staking_router_stub,
    node_operator,
):
    """Test that a valid exit request with creator address passes validation."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["curated"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    submit_exit_request_hashes_utils_wrapper.validateExitRequests(
        [request.to_tuple()],
        curated_registry_stub,
        staking_router_stub,
        node_operator.address,  # Pass the creator address
    )


def test_validation_reverts_if_creator_not_node_operator_multiple(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    curated_registry_stub,
    staking_router_stub,
):
    """Test that a valid exit request with a creator not in the registry reverts when multiple requests are present."""

    node_op_id = add_node_operator(
        curated_registry_stub,
        submit_exit_hashes_factory_config["pubkeys"][1],
    )
    request1 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["curated"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )
    request2 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["curated"],
        node_op_id,  # Use a different node operator ID
        submit_exit_hashes_factory_config["validator_index"] + 1,
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    # Use an address that is not in the registry
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request1.to_tuple(), request2.to_tuple()],
            curated_registry_stub,
            staking_router_stub,
            accounts[0].address,  # Pass a non-registry address
        )


def test_validation_reverts_on_empty_requests(
    submit_exit_request_hashes_utils_wrapper,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that an empty exit request list reverts."""
    with reverts("EMPTY_REQUESTS_LIST"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_too_many_requests(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that a request with too many requests reverts."""
    # Create a request with the maximum allowed number of requests
    max_requests = submit_exit_hashes_factory_config["max_requests_per_motion"]
    requests = [
        exit_request_input_factory(
            submit_exit_hashes_factory_config["module_ids"]["sdvt"],
            submit_exit_hashes_factory_config["node_op_id"],
            i,
            submit_exit_hashes_factory_config["pubkeys"][i],
            i,
        ).to_tuple()
        for i in range(max_requests)
    ]

    # This should pass
    submit_exit_request_hashes_utils_wrapper.validateExitRequests(
        requests, sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
    )

    # Now create one more request, which should cause a revert
    extra_request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        max_requests,
    )

    with reverts("MAX_REQUESTS_PER_MOTION_EXCEEDED"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            requests + [extra_request.to_tuple()], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_wrong_staking_module(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that a request with a wrong staking module reverts."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["curated"],  # Set it to wrong
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry_stub,  # Use the SDVT registry to validate the request, should fail
            staking_router_stub,
            ZERO_ADDRESS,
        )


def test_validation_reverts_on_wrong_staking_module_multiple(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
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
        submit_exit_hashes_factory_config["module_ids"]["curated"],  # Set it to wrong
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request1.to_tuple(), request2.to_tuple()],
            sdvt_registry_stub,  # Use the SDVT registry to validate the request, should fail
            staking_router_stub,
            ZERO_ADDRESS,
        )


def test_validation_reverts_on_empty_pubkey(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
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

    with reverts("INVALID_PUBKEY_LENGTH"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_pubkey_too_short(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
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
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_pubkey_too_long(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
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
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_wrong_pubkey(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
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
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_wrong_node_op_id(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that a request with a wrong node operator ID reverts."""
    last_node_op_id = sdvt_registry_stub.getNodeOperatorsCount()
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        last_node_op_id + 1,  # Use an invalid node operator ID
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_wrong_node_op_id_multiple(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
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

    last_node_op_id = sdvt_registry_stub.getNodeOperatorsCount()
    request2 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        last_node_op_id + 1,  # Use an invalid node operator ID
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request1.to_tuple(), request2.to_tuple()], sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_duplicate_exit_requests(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that a request with duplicate entries reverts."""
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    # Create a list with duplicates
    requests_with_duplicates = [request.to_tuple(), request.to_tuple()]

    with reverts("INVALID_EXIT_REQUESTS_SORT_ORDER"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            requests_with_duplicates, sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS
        )


def test_validation_reverts_on_wrong_requests_index_sort_order(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that a request with a wrong validator index sort order reverts."""
    request1 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        1,  # Validator index 1
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )
    request2 = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        submit_exit_hashes_factory_config["node_op_id"],
        0,  # Validator index 0 (out of order)
        submit_exit_hashes_factory_config["pubkeys"][1],
        0,
    )

    with reverts("INVALID_EXIT_REQUESTS_SORT_ORDER"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request1.to_tuple(), request2.to_tuple()],
            sdvt_registry_stub,
            staking_router_stub,
            ZERO_ADDRESS,
        )


def test_validation_reverts_on_module_id_overflow(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that a request with a moduleId exceeding uint24 reverts."""
    invalid_module_id = 2**24  # Set the moduleId to a value that exceeds uint24

    staking_router_stub.setStakingModule(
        invalid_module_id, sdvt_registry_stub.address
    )  # Set the count to a value that exceeds uint24

    # Create a request with moduleId exceeding uint24
    request = exit_request_input_factory(
        invalid_module_id,  # moduleId exceeds uint24
        submit_exit_hashes_factory_config["node_op_id"],
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    # module id in the staking router is rounded to uint24, so it will not find the overflowed module id
    with reverts("EXECUTOR_NOT_PERMISSIONED_ON_MODULE"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry_stub,
            staking_router_stub,
            ZERO_ADDRESS,
        )


def test_validation_reverts_on_node_op_id_overflow(
    submit_exit_request_hashes_utils_wrapper,
    exit_request_input_factory,
    submit_exit_hashes_factory_config,
    sdvt_registry_stub,
    staking_router_stub,
):
    """Test that a request with a nodeOpId exceeding uint40 reverts."""
    invalid_node_op_id = 2**40  # Set the nodeOpId to a value that exceeds uint40

    sdvt_registry_stub.setDesiredNodeOperatorCount(
        invalid_node_op_id + 1
    )  # Set the count to a value that exceeds uint40

    # Create a request with nodeOpId exceeding uint40
    request = exit_request_input_factory(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"],
        invalid_node_op_id,  # nodeOpId exceeds uint40
        submit_exit_hashes_factory_config["validator_index"],
        submit_exit_hashes_factory_config["pubkeys"][0],
        0,
    )

    # node operator id in the registry is rounded to uint40, so it will not find the overflowed node operator id
    with reverts("NODE_OPERATOR_ID_DOES_NOT_EXIST"):
        submit_exit_request_hashes_utils_wrapper.validateExitRequests(
            [request.to_tuple()],
            sdvt_registry_stub,
            staking_router_stub,
            ZERO_ADDRESS,
        )


def test_hash_requests(
    submit_exit_request_hashes_utils_wrapper,
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

    actual_hash = submit_exit_request_hashes_utils_wrapper.hashExitRequests([request.to_tuple()])

    assert actual_hash == expected_hash


def test_hash_requests_multiple(
    submit_exit_request_hashes_utils_wrapper,
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

    actual_hash = submit_exit_request_hashes_utils_wrapper.hashExitRequests([request1.to_tuple(), request2.to_tuple()])

    assert actual_hash == expected_hash


def test_hash_requests_empty(
    submit_exit_request_hashes_utils_wrapper,
    submit_exit_hashes_factory_config,
):
    """Test that hashing an empty request list returns the expected hash."""
    expected_hash = create_exit_requests_hashes([], submit_exit_hashes_factory_config["data_format"])

    actual_hash = submit_exit_request_hashes_utils_wrapper.hashExitRequests([])

    assert actual_hash == expected_hash
