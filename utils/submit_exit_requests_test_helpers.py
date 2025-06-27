import time
import brownie
from brownie import chain, web3, accounts
from eth_abi import encode
from utils.evm_script import encode_calldata

# Key and signature lengths for exit-request keys
PUBKEY_SIZE = 48
SIG_SIZE = 96
MAX_REQUESTS = 250
DATA_FORMAT_LIST = 1


def create_exit_request_hash_calldata(exit_request_inputs: list):
    return encode_calldata(
        ["(uint256,uint256,uint64,bytes,uint256)[]"],
        [exit_request_inputs],
    )


def create_exit_request_data(requests):
    # helper to normalize pubkey to raw bytes
    def _pub(r):
        if isinstance(r.val_pubkey, str):
            h = r.val_pubkey[2:] if r.val_pubkey.startswith("0x") else r.val_pubkey
            return bytes.fromhex(h)
        return r.val_pubkey

    return b"".join(
        r.module_id.to_bytes(3, "big") + r.node_op_id.to_bytes(5, "big") + r.val_index.to_bytes(8, "big") + _pub(r)
        for r in requests
    )


def create_exit_requests_hashes(requests, data_format=1):
    """
    requests: list of objects with attributes
      - moduleId: int
      - nodeOpId: int
      - valIndex: int
      - valPubkey: str or bytes (48-byte hex str with '0x' or raw bytes)
    """

    # abi.encode(bytes, uint256) then keccak256
    digest = web3.keccak(encode(["bytes", "uint256"], [create_exit_request_data(requests), data_format]))
    return digest.hex()


def make_test_bytes(i: int, length: int = 48) -> bytes:
    """
    Generate a test byte sequence for key or signature of arbitrary length.
    First 3 bytes: index (big-endian),
    Rest: repeat of (i mod 256).
    """
    idx_bytes = i.to_bytes(3, "big")
    if length < 3:
        raise ValueError("Length must be at least 3 bytes")
    return idx_bytes + bytes([i % 256]) * (length - 3)


def add_node_operator(registry_stub, pubkey):
    registry_stub.addNodeOperator(
        "test_node_op_1", accounts[0].address, 200, 400
    )  # Add a node operator to the registry
    new_node_op_id = registry_stub.getNodeOperatorsCount() - 1

    registry_stub.setSigningKeys(
        new_node_op_id,
        pubkey,
    )

    return new_node_op_id


def ensure_single_operator_with_keys(registry, min_keys):
    count = registry.getNodeOperatorsCount()
    if count == 0:
        raise ValueError("No node operators found")

    op_id = 0
    _, _, op_addr, _, _, total_keys, _ = registry.getNodeOperator(op_id, False)
    while total_keys == 0:
        op_id += 1
        _, _, op_addr, _, _, total_keys, _ = registry.getNodeOperator(op_id, False)

    BATCH = 10

    existing = total_keys

    if total_keys < min_keys:
        to_add = min_keys - existing
        print(f"→ need {to_add} more keys (to reach {min_keys})")

        for start in range(existing, existing + to_add, BATCH):
            end = min(start + BATCH, existing + to_add)
            count = end - start

            # build batch buffers
            buf_keys = bytearray(PUBKEY_SIZE * count)
            buf_sigs = bytearray(SIG_SIZE * count)
            for idx, i in enumerate(range(start, end)):
                buf_keys[idx * PUBKEY_SIZE : (idx + 1) * PUBKEY_SIZE] = make_test_bytes(i, PUBKEY_SIZE)
                buf_sigs[idx * SIG_SIZE : (idx + 1) * SIG_SIZE] = make_test_bytes(i, SIG_SIZE)

            hex_keys = "0x" + buf_keys.hex()
            hex_sigs = "0x" + buf_sigs.hex()

            registry.addSigningKeys(op_id, count, hex_keys, hex_sigs, {"from": op_addr})

    return op_id, op_addr


def grant_submit_report_hash_role(agent, oracle, easy_track):
    """
    Grant EasyTrack`s script executor the SUBMIT_REPORT_HASH_ROLE
    so it can call submitExitRequestsData on the oracle.
    """
    role = oracle.SUBMIT_REPORT_HASH_ROLE()
    executor = easy_track.evmScriptExecutor()

    if not oracle.hasRole(role, executor):
        oracle.grantRole(role, executor, {"from": agent})


def get_operator_keys(registry, operator, num_keys):
    """
    Return up to `num_keys` signing keys for operator ID 0,
    as a list of (index, pubkey_bytes).
    """
    pubkeys_bytes, _, _ = registry.getSigningKeys(operator, 0, num_keys)
    count = len(pubkeys_bytes) // PUBKEY_SIZE
    return [(i, pubkeys_bytes[i * PUBKEY_SIZE : (i + 1) * PUBKEY_SIZE]) for i in range(count)]


def build_exit_requests(request_input_factory, module_id, node_op_id, key_entries):
    """
    Convert a list of (index, pubkey) entries into exit-request objects
    all targeting node_operator_id = 0.
    """
    return [
        request_input_factory(
            module_id=module_id,
            node_op_id=node_op_id,
            val_index=index,
            val_pubkey=pubkey,
            val_pubkey_index=index,
        )
        for index, pubkey in key_entries
    ]


def validate_exit_events(exit_requests, events):
    """
    Ensure each ValidatorExitRequest event matches the original request data.
    """
    assert len(events) == len(exit_requests)
    for event, request in zip(events, exit_requests):
        assert event["stakingModuleId"] == request.module_id
        assert event["nodeOperatorId"] == request.node_op_id
        assert event["validatorIndex"] == request.val_index
        assert event["validatorPubkey"] == "0x" + request.val_pubkey.hex()


def run_motion_and_check_events(factory, create_motion_fn, submit_fn, easy_track, oracle, exit_requests, stranger):
    """
    Orchestrate an EasyTrack motion:
    • submit the exit-hash calldata
    • verify the oracle rejects until enactment
    • advance time and enact the motion
    • confirm the hash event is emitted
    • submit the full exit batch to the oracle and validate each event
    """
    calldata = create_exit_request_hash_calldata([r.to_tuple() for r in exit_requests])
    motion_tx = create_motion_fn(factory, calldata)
    motion_id = easy_track.getMotions()[0][0]
    evm_data = motion_tx.events["MotionCreated"]["_evmScriptCallData"]

    packed = create_exit_request_data(exit_requests)

    with brownie.reverts("ExitHashNotSubmitted: "):
        submit_fn((packed, DATA_FORMAT_LIST))

    chain.sleep(easy_track.motionDuration() + 5)
    enact_tx = easy_track.enactMotion(motion_id, evm_data, {"from": stranger})

    expected_hash = create_exit_requests_hashes(exit_requests)
    hash_events = enact_tx.events["RequestsHashSubmitted"]
    assert all(h["exitRequestsHash"] == expected_hash for h in hash_events)

    final_tx = submit_fn((packed, DATA_FORMAT_LIST))
    validate_exit_events(exit_requests, final_tx.events["ValidatorExitRequest"])
