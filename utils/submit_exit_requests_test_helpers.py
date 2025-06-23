import brownie
from brownie import chain, web3, accounts
from eth_abi import encode
from utils.evm_script import encode_call_script, encode_calldata

# Key and signature lengths for exit-request keys
PUBKEY_SIZE = 48
SIG_SIZE = 96

# Maximum batch size for exit requests
MAX_KEYS = 200

# Format identifier for batched oracle submissions
DATA_FORMAT_LIST = 1


def create_exit_request_hash_calldata(exit_request_inputs: list):
    return encode_calldata(
        ["(uint256,uint256,uint64,bytes,uint256)[]"],
        [exit_request_inputs],
    )


def create_exit_requests_hashes(requests, data_format=1):
    """
    requests: list of objects with attributes
      - moduleId: int
      - nodeOpId: int
      - valIndex: int
      - valPubkey: str or bytes (48-byte hex str with '0x' or raw bytes)
    """

    # helper to normalize pubkey to raw bytes
    def _pub(r):
        if isinstance(r.val_pubkey, str):
            h = r.val_pubkey[2:] if r.val_pubkey.startswith("0x") else r.val_pubkey
            return bytes.fromhex(h)
        return r.val_pubkey

    packed = b"".join(
        r.module_id.to_bytes(3, "big") + r.node_op_id.to_bytes(5, "big") + r.val_index.to_bytes(8, "big") + _pub(r)
        for r in requests
    )

    # abi.encode(bytes, uint256) then keccak256
    digest = web3.keccak(encode(["bytes", "uint256"], [packed, data_format]))
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


def ensure_single_operator_with_keys_via_vote(registry, accounts, acl, voting, agent, lido_contracts, min_keys):
    """
    Use on-chain governance motions to add precisely one node operator (ID 0)
    and ensure it holds at least `min_keys` signing keys. Returns the operator’s address.
    """
    operator_info = {"name": "test_node_operator", "address": accounts[3]}
    manage_role = registry.MANAGE_NODE_OPERATOR_ROLE()

    # If voting cannot yet manage operators, grant it that power.
    if not acl.hasPermission(voting, registry.address, manage_role):
        grant_script = encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(voting, registry.address, manage_role),
                ),
            ]
        )
        vote_id, _ = lido_contracts.create_voting(
            evm_script=grant_script,
            description="Allow governance to manage node operators",
            tx_params={"from": agent},
        )
        lido_contracts.execute_voting(vote_id)

    # If the registry is empty, add our test operator via vote.
    if registry.getNodeOperatorsCount() == 0:
        add_call = registry.addNodeOperator.encode_input(operator_info["name"], operator_info["address"])
        add_script = encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(voting, registry.address, manage_role),
                ),
                (
                    registry.address,
                    add_call,
                ),
            ]
        )
        vote_id, _ = lido_contracts.create_voting(
            evm_script=add_script,
            description="Register test node operator",
            tx_params={"from": agent},
        )
        lido_contracts.execute_voting(vote_id)

    # Fetch existing keys for operator #0 and top up if fewer than `min_keys`.
    pubkeys_bytes, _, _ = registry.getSigningKeys(0, 0, min_keys)
    existing = len(pubkeys_bytes) // PUBKEY_SIZE
    if existing < min_keys:
        to_add = min_keys - existing
        keys = b"".join(make_test_bytes(i, PUBKEY_SIZE) for i in range(existing, existing + to_add))
        sigs = b"".join(make_test_bytes(i, SIG_SIZE) for i in range(existing, existing + to_add))
        registry.addSigningKeys(0, to_add, "0x" + keys.hex(), "0x" + sigs.hex(), {"from": operator_info["address"]})

    return operator_info["address"]


def grant_submit_report_hash_role(lido_contracts, acl, voting, agent, oracle, easy_track):
    """
    Grant EasyTrack`s script executor the SUBMIT_REPORT_HASH_ROLE
    so it can call submitExitRequestsData on the oracle.
    """
    role = oracle.SUBMIT_REPORT_HASH_ROLE()
    executor = easy_track.evmScriptExecutor()

    if not acl.hasPermission(executor, oracle.address, role):
        script = encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(executor, oracle.address, role),
                ),
            ]
        )
        vote_id, _ = lido_contracts.create_voting(
            evm_script=script,
            description="Allow EasyTrack executor to submit exit hashes",
            tx_params={"from": agent},
        )
        lido_contracts.execute_voting(vote_id)


def get_operator_keys(registry, num_keys):
    """
    Return up to `num_keys` signing keys for operator ID 0,
    as a list of (index, pubkey_bytes).
    """
    pubkeys_bytes, _, _ = registry.getSigningKeys(0, 0, num_keys)
    count = len(pubkeys_bytes) // PUBKEY_SIZE
    return [(i, pubkeys_bytes[i * PUBKEY_SIZE : (i + 1) * PUBKEY_SIZE]) for i in range(count)]


def build_exit_requests(request_input_factory, module_id, key_entries):
    """
    Convert a list of (index, pubkey) entries into exit-request objects
    all targeting node_operator_id = 0.
    """
    return [
        request_input_factory(
            module_id=module_id,
            node_op_id=0,
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
        assert event["validatorPubkey"] == request.val_pubkey


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

    packed = b"".join(r.to_bytes() for r in exit_requests)

    with brownie.reverts("ExitHashNotSubmitted"):
        submit_fn((packed, DATA_FORMAT_LIST))

    chain.sleep(easy_track.motionDuration() + 5)
    enact_tx = easy_track.enactMotion(motion_id, evm_data, {"from": stranger})

    expected_hash = create_exit_requests_hashes(exit_requests)
    hash_events = enact_tx.events.get("RequestsHashSubmitted", [])
    assert any(h["exitRequestsHash"] == expected_hash for h in hash_events)

    final_tx = submit_fn((packed, DATA_FORMAT_LIST))
    validate_exit_events(exit_requests, final_tx.events["ValidatorExitRequest"])
