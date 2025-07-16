from utils.submit_exit_requests_test_helpers import (
    ensure_single_operator_with_keys,
    get_operator_keys,
    build_exit_requests,
    run_motion_and_check_events,
    grant_submit_report_hash_role,
    MAX_REQUESTS,
)

MODULE_ID = 1


def create_motion_curated(factory, calldata, caller, easy_track):
    """
    Curated motions must be started by the node operator`s reward address.
    """
    return easy_track.createMotion(factory, calldata, {"from": caller})


def submit_exit_data_curated(data, oracle, caller):
    """
    The same reward address is used to submit the exit-requests batch to the oracle.
    """
    return oracle.submitExitRequestsData(data, {"from": caller})


def test_curated_single_exit_request_happy_path(
    curated_submit_exit_hashes_evm_script_factory,
    curated_registry,
    easy_track,
    validators_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    agent,
):
    grant_submit_report_hash_role(agent, validators_exit_bus_oracle, easy_track)

    node_operator_id, reward_address = ensure_single_operator_with_keys(curated_registry, 1)

    key_list = get_operator_keys(curated_registry, node_operator_id, 1)
    requests = build_exit_requests(exit_request_input_factory, MODULE_ID, node_operator_id, key_list)

    run_motion_and_check_events(
        factory=curated_submit_exit_hashes_evm_script_factory,
        create_motion_fn=lambda f, c: create_motion_curated(f, c, reward_address, easy_track),
        submit_fn=lambda d: submit_exit_data_curated(d, validators_exit_bus_oracle, reward_address),
        easy_track=easy_track,
        oracle=validators_exit_bus_oracle,
        exit_requests=requests,
        stranger=stranger,
    )


def test_curated_batch_exit_requests_happy_path(
    curated_submit_exit_hashes_evm_script_factory,
    curated_registry,
    easy_track,
    validators_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    agent,
):
    grant_submit_report_hash_role(agent, validators_exit_bus_oracle, easy_track)

    node_operator_id, reward_address = ensure_single_operator_with_keys(curated_registry, MAX_REQUESTS)

    key_list = get_operator_keys(curated_registry, node_operator_id, MAX_REQUESTS)
    requests = build_exit_requests(exit_request_input_factory, MODULE_ID, node_operator_id, key_list)

    assert len(requests) == MAX_REQUESTS

    run_motion_and_check_events(
        factory=curated_submit_exit_hashes_evm_script_factory,
        create_motion_fn=lambda f, c: create_motion_curated(f, c, reward_address, easy_track),
        submit_fn=lambda d: submit_exit_data_curated(d, validators_exit_bus_oracle, reward_address),
        easy_track=easy_track,
        oracle=validators_exit_bus_oracle,
        exit_requests=requests,
        stranger=stranger,
    )
