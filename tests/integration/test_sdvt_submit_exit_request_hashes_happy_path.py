from utils.submit_exit_requests_test_helpers import (
    ensure_single_operator_with_keys,
    get_operator_keys,
    build_exit_requests,
    run_motion_and_check_events,
    grant_submit_report_hash_role,
    create_exit_request_hash_calldata,
    make_test_bytes,
    MAX_REQUESTS,
)
from brownie import reverts
import pytest
from utils.test_helpers import set_account_balance

MODULE_ID = 2


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
    sdvt_trusted_caller,
    easy_track,
    validators_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    agent,
):
    grant_submit_report_hash_role(agent, validators_exit_bus_oracle, easy_track)

    node_operator_id, _ = ensure_single_operator_with_keys(sdvt_registry, 1)

    key_list = get_operator_keys(sdvt_registry, node_operator_id, 1)
    requests = build_exit_requests(exit_request_input_factory, MODULE_ID, node_operator_id, key_list)

    run_motion_and_check_events(
        factory=sdvt_submit_exit_hashes_evm_script_factory,
        create_motion_fn=lambda f, c: create_motion_sdvt(f, c, sdvt_trusted_caller, easy_track),
        submit_fn=lambda d: submit_exit_data_sdvt(d, validators_exit_bus_oracle, sdvt_trusted_caller),
        easy_track=easy_track,
        oracle=validators_exit_bus_oracle,
        exit_requests=requests,
        stranger=stranger,
    )


def test_sdvt_batch_exit_requests_happy_path(
    sdvt_submit_exit_hashes_evm_script_factory,
    sdvt_registry,
    sdvt_trusted_caller,
    easy_track,
    validators_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    agent,
):
    batch_size = 60
    grant_submit_report_hash_role(agent, validators_exit_bus_oracle, easy_track)

    node_operator_id, _ = ensure_single_operator_with_keys(sdvt_registry, batch_size)

    key_list = get_operator_keys(sdvt_registry, node_operator_id, batch_size)
    requests = build_exit_requests(exit_request_input_factory, MODULE_ID, node_operator_id, key_list)

    assert len(requests) == batch_size

    run_motion_and_check_events(
        factory=sdvt_submit_exit_hashes_evm_script_factory,
        create_motion_fn=lambda f, c: create_motion_sdvt(f, c, sdvt_trusted_caller, easy_track),
        submit_fn=lambda d: submit_exit_data_sdvt(d, validators_exit_bus_oracle, sdvt_trusted_caller),
        easy_track=easy_track,
        oracle=validators_exit_bus_oracle,
        exit_requests=requests,
        stranger=stranger,
    )


def test_sdvt_reverts_on_unused_key(
    sdvt_submit_exit_hashes_evm_script_factory,
    sdvt_registry,
    sdvt_trusted_caller,
    easy_track,
    validators_exit_bus_oracle,
    exit_request_input_factory,
    agent,
):
    grant_submit_report_hash_role(agent, validators_exit_bus_oracle, easy_track)

    node_operator_id, op_addr = ensure_single_operator_with_keys(sdvt_registry, 1)
    set_account_balance(op_addr)

    key_list = get_operator_keys(sdvt_registry, node_operator_id, 1)
    requests = build_exit_requests(exit_request_input_factory, MODULE_ID, node_operator_id, key_list)

    # Create an unused key by adding a fresh signing key (used=false by default)
    _, _, _, _, _, total_signing_keys, _ = sdvt_registry.getNodeOperator(node_operator_id, False)
    new_key = make_test_bytes(total_signing_keys, 48)
    new_sig = make_test_bytes(total_signing_keys, 96)
    sdvt_registry.addSigningKeys(
        node_operator_id, 1, "0x" + new_key.hex(), "0x" + new_sig.hex(), {"from": op_addr}
    )

    _, _, bool_used = sdvt_registry.getSigningKey(node_operator_id, total_signing_keys)
    assert not bool_used, "Test setup failure: expected the new key to be unused"

    request_unused = exit_request_input_factory(
        MODULE_ID,
        node_operator_id,
        total_signing_keys,
        new_key,
        total_signing_keys,
    )
    requests = [request_unused]

    calldata = create_exit_request_hash_calldata([r.to_tuple() for r in requests])

    with reverts("UNUSED_PUBKEY"):
        create_motion_sdvt(
            sdvt_submit_exit_hashes_evm_script_factory,
            calldata,
            sdvt_trusted_caller,
            easy_track,
        )
