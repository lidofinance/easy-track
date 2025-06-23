from utils.submit_exit_requests_test_helpers import (
    ensure_single_operator_with_keys_via_vote,
    get_operator_keys,
    build_exit_requests,
    run_motion_and_check_events,
    grant_submit_report_hash_role,
    MAX_KEYS,
)


def create_motion_sdvt(factory, calldata, multisig, easy_track):
    """
    The SDVT module requires motions to be initiated by the multisig address.
    """
    return easy_track.createMotion(factory, calldata, {"from": multisig})


def submit_exit_data_sdvt(data, oracle, multisig):
    """
    SDVT exit batches are also submitted to the oracle by the multisig.
    """
    return oracle.submitExitRequestsData(data, {"from": multisig})


def test_sdvt_single_exit_request_happy_path(
    sdvt_submit_exit_hashes_evm_script_factory,
    sdvt_registry,
    sdvt_multisig,
    easy_track,
    lido_contracts,
    validator_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    accounts,
    acl,
    voting,
    agent,
):
    grant_submit_report_hash_role(lido_contracts, acl, voting, agent, validator_exit_bus_oracle, easy_track)

    ensure_single_operator_with_keys_via_vote(sdvt_registry, accounts, acl, voting, agent, lido_contracts, min_keys=1)

    key_list = get_operator_keys(sdvt_registry, 1)
    requests = build_exit_requests(
        exit_request_input_factory, sdvt_submit_exit_hashes_evm_script_factory.moduleId(), key_list
    )

    run_motion_and_check_events(
        factory=sdvt_submit_exit_hashes_evm_script_factory,
        create_motion_fn=lambda f, c: create_motion_sdvt(f, c, sdvt_multisig, easy_track),
        submit_fn=lambda d: submit_exit_data_sdvt(d, validator_exit_bus_oracle, sdvt_multisig),
        easy_track=easy_track,
        oracle=validator_exit_bus_oracle,
        exit_requests=requests,
        stranger=stranger,
    )


def test_sdvt_batch_exit_requests_happy_path(
    sdvt_submit_exit_hashes_evm_script_factory,
    sdvt_registry,
    sdvt_multisig,
    easy_track,
    lido_contracts,
    validator_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    accounts,
    acl,
    voting,
    agent,
):
    grant_submit_report_hash_role(lido_contracts, acl, voting, agent, validator_exit_bus_oracle, easy_track)

    ensure_single_operator_with_keys_via_vote(
        sdvt_registry, accounts, acl, voting, agent, lido_contracts, min_keys=MAX_KEYS
    )

    key_list = get_operator_keys(sdvt_registry, MAX_KEYS)
    requests = build_exit_requests(
        exit_request_input_factory, sdvt_submit_exit_hashes_evm_script_factory.moduleId(), key_list
    )
    assert len(requests) == MAX_KEYS

    run_motion_and_check_events(
        factory=sdvt_submit_exit_hashes_evm_script_factory,
        create_motion_fn=lambda f, c: create_motion_sdvt(f, c, sdvt_multisig, easy_track),
        submit_fn=lambda d: submit_exit_data_sdvt(d, validator_exit_bus_oracle, sdvt_multisig),
        easy_track=easy_track,
        oracle=validator_exit_bus_oracle,
        exit_requests=requests,
        stranger=stranger,
    )
