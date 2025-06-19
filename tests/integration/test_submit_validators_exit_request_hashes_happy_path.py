import pytest
import brownie
from brownie import convert, reverts
from utils.evm_script import encode_call_script
from utils.test_helpers import make_test_bytes, create_exit_request_hash_calldata, create_exit_requests_hashes

NUM_OPERATORS = 51
MIN_KEYS_PER_OPERATOR = 4
PUBKEY_SIZE = 48
SIG_SIZE = 96
DATA_FORMAT_LIST = 1

MODULES = [
    {
        "name": "sdvt",
        "module_id": 2,
        "factory_fixture": "sdvt_submit_exit_hashes_evm_script_factory",
        "registry_fixture": "sdvt_registry",
        "multisig_fixture": "sdvt_multisig",
    },
    {
        "name": "curated",
        "module_id": 1,
        "factory_fixture": "curated_submit_exit_hashes_evm_script_factory",
        "registry_fixture": "curated_registry",
        "multisig_fixture": "curated_multisig",
    },
]


def ensure_operators_with_keys(
    registry,
    accounts,
    acl,
    voting,
    agent,
    lido_contracts,
    required_operator_count=NUM_OPERATORS,
    min_keys=MIN_KEYS_PER_OPERATOR,
):
    """
    Ensure the registry has the required number of node operators, and each has at least `min_keys` signing keys.
    All operators use accounts[1] for simplicity.
    Only grants MANAGE_NODE_OPERATOR_ROLE if not present.
    """
    operator_address = accounts[1]
    manage_role = registry.MANAGE_NODE_OPERATOR_ROLE()
    registry_address = registry.address

    # Grant permission to voting to manage node operators (only if needed)
    if not acl.hasPermission(voting, registry_address, manage_role):
        permission_script = encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(voting, registry_address, manage_role),
                ),
            ]
        )
        vote_id, _ = lido_contracts.create_voting(
            evm_script=permission_script,
            description="Grant node operator manage permission",
            tx_params={"from": agent},
        )
        lido_contracts.execute_voting(vote_id)

    # Add node operators if missing
    current_count = registry.getNodeOperatorsCount()
    for op_id in range(current_count, required_operator_count):
        registry.addNodeOperator(f"op_{op_id}", operator_address, {"from": agent})

    # Add signing keys as needed
    for op_id in range(required_operator_count):
        pubkeys_bytes, _, _ = registry.getSigningKeys(op_id, 0, min_keys)
        key_count = len(pubkeys_bytes) // PUBKEY_SIZE

        if key_count < min_keys:
            offset = key_count
            keys_to_add = min_keys - key_count
            pubkeys = b"".join(
                make_test_bytes(op_id * min_keys + i, PUBKEY_SIZE) for i in range(offset, offset + keys_to_add)
            )
            sigs = b"".join(
                make_test_bytes(op_id * min_keys + i, SIG_SIZE) for i in range(offset, offset + keys_to_add)
            )
            registry.addSigningKeys(
                op_id,
                keys_to_add,
                "0x" + pubkeys.hex(),
                "0x" + sigs.hex(),
                {"from": operator_address},
            )


def get_operator_keys(registry, operator_id, num_keys):
    """
    Return [(key_index, pubkey-bytes)] for one operator.
    """
    pubkeys_bytes, _, _ = registry.getSigningKeys(operator_id, 0, num_keys)
    return [
        (key_index, pubkeys_bytes[key_index * PUBKEY_SIZE : (key_index + 1) * PUBKEY_SIZE])
        for key_index in range(num_keys)
    ]


def build_exit_requests(request_input_factory, module_id, operator_id, key_entries):
    """
    Build exit request objects for a given operator and a list of (key_index, pubkey-bytes).
    """
    return [
        request_input_factory(
            module_id=module_id,
            node_op_id=operator_id,
            val_index=key_index,
            val_pubkey=pubkey_bytes,
            val_pubkey_index=key_index,
        )
        for key_index, pubkey_bytes in key_entries
    ]


def run_motion_and_check_events(
    factory,
    multisig,
    easy_track,
    oracle_contract,
    exit_requests,
    stranger_account,
):
    # Build the motion calldata
    calldata = create_exit_request_hash_calldata([request.to_tuple() for request in exit_requests])
    motion_tx = easy_track.createMotion(factory, calldata, {"from": multisig})
    motion_id = easy_track.getMotions()[0][0]
    evm_script_call_data = motion_tx.events["MotionCreated"]["_evmScriptCallData"]

    packed_requests = b"".join(convert.to_bytes(request.to_tuple()) for request in exit_requests)

    # Before hash is submitted, should revert
    with reverts("ExitHashNotSubmitted"):
        oracle_contract.submitExitRequestsData((packed_requests, DATA_FORMAT_LIST), {"from": multisig})

    brownie.chain.sleep(easy_track.motionDuration() + 5)
    enact_tx = easy_track.enactMotion(motion_id, evm_script_call_data, {"from": stranger_account})

    expected_hash = create_exit_requests_hashes(exit_requests)
    hash_events = enact_tx.events["RequestsHashSubmitted"]
    assert any(event["exitRequestsHash"] == expected_hash for event in hash_events)

    # Now submit the batch to the oracle, should succeed
    oracle_tx = oracle_contract.submitExitRequestsData((packed_requests, DATA_FORMAT_LIST), {"from": multisig})
    validator_exit_events = oracle_tx.events["ValidatorExitRequest"]

    assert len(validator_exit_events) == len(exit_requests)
    for event, request in zip(validator_exit_events, exit_requests):
        assert event["stakingModuleId"] == request.module_id
        assert event["nodeOperatorId"] == request.node_op_id
        assert event["validatorIndex"] == request.val_index
        assert event["validatorPubkey"] == request.val_pubkey


@pytest.mark.parametrize("module", MODULES, ids=[mod["name"] for mod in MODULES])
def test_single_exit_request_happy_path(
    module,
    request,
    easy_track,
    lido_contracts,
    validator_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    accounts,
):
    """
    Test a single exit request (first operator, first key).
    """
    factory = request.getfixturevalue(module["factory_fixture"])
    registry = request.getfixturevalue(module["registry_fixture"])
    multisig = request.getfixturevalue(module["multisig_fixture"])

    ensure_operators_with_keys(
        registry=registry,
        accounts=accounts,
        acl=lido_contracts.aragon.acl,
        voting=lido_contracts.aragon.voting,
        agent=lido_contracts.aragon.agent,
        lido_contracts=lido_contracts,
        required_operator_count=NUM_OPERATORS,
        min_keys=MIN_KEYS_PER_OPERATOR,
    )

    key_entries = get_operator_keys(registry, 0, MIN_KEYS_PER_OPERATOR)
    single_exit_request = build_exit_requests(
        exit_request_input_factory,
        module["module_id"],
        0,
        [key_entries[0]],
    )

    run_motion_and_check_events(
        factory=factory,
        multisig=multisig,
        easy_track=easy_track,
        oracle_contract=validator_exit_bus_oracle,
        exit_requests=single_exit_request,
        stranger_account=stranger,
    )


@pytest.mark.parametrize("module", MODULES, ids=[mod["name"] for mod in MODULES])
def test_batch_exit_requests_happy_path(
    module,
    request,
    easy_track,
    lido_contracts,
    validator_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    accounts,
):
    """
    Test batch flow: 50 operators (1-50), 4 keys each, total 200 requests.
    """
    factory = request.getfixturevalue(module["factory_fixture"])
    registry = request.getfixturevalue(module["registry_fixture"])
    multisig = request.getfixturevalue(module["multisig_fixture"])

    ensure_operators_with_keys(
        registry=registry,
        accounts=accounts,
        acl=lido_contracts.aragon.acl,
        voting=lido_contracts.aragon.voting,
        agent=lido_contracts.aragon.agent,
        lido_contracts=lido_contracts,
        required_operator_count=NUM_OPERATORS,
        min_keys=MIN_KEYS_PER_OPERATOR,
    )

    batch_exit_requests = []
    for operator_id in range(1, NUM_OPERATORS):
        key_entries = get_operator_keys(registry, operator_id, MIN_KEYS_PER_OPERATOR)
        batch_exit_requests.extend(
            build_exit_requests(
                exit_request_input_factory,
                module["module_id"],
                operator_id,
                key_entries,
            )
        )

    assert len(batch_exit_requests) == (NUM_OPERATORS - 1) * MIN_KEYS_PER_OPERATOR

    run_motion_and_check_events(
        factory=factory,
        multisig=multisig,
        easy_track=easy_track,
        oracle_contract=validator_exit_bus_oracle,
        exit_requests=batch_exit_requests,
        stranger_account=stranger,
    )
