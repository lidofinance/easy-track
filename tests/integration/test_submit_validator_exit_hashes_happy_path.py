import pytest
import brownie
from brownie import convert, reverts
from utils.evm_script import encode_call_script

MODULES = [
    {
        "name": "sdvt",
        "factory_fixture": "sdvt_submit_exit_hashes_evm_script_factory",
        "registry_fixture": "sdvt_registry",
        "multisig_fixture": "sdvt_multisig",
        "module_id_key": "sdvt",
    },
    {
        "name": "curated",
        "factory_fixture": "curated_submit_exit_hashes_evm_script_factory",
        "registry_fixture": "curated_registry",
        "multisig_fixture": "curated_multisig",
        "module_id_key": "curated",
    },
]

PUBKEYS = [
    "8bb1db218877a42047b953bdc32573445a78d93383ef5fd08f79c066d4781961db4f5ab5a7cc0cf1e4cbcc23fd17f9d7",
]
SIGNATURES = [
    "ad17ef7cdf0c4917aaebc067a785b049d417dda5d4dd66395b21bbd50781d51e28ee750183eca3d32e1f57b324049a06135ad07d1aa243368bca9974e25233f050e0d6454894739f87faace698b90ea65ee4baba2758772e09fec4f1d8d35660",
]

DATA_FORMAT_LIST = 1


def ensure_node_operators_and_keys(
    registry,
    lido_contracts,
    accounts,
    voting,
    agent,
    acl,
    min_count=300,
    pubkeys=PUBKEYS,
    signatures=SIGNATURES,
):
    """Ensures the registry has at least `min_count` node operators, each with at least one pubkey."""
    existing_count = registry.getNodeOperatorsCount()
    for i in range(existing_count, min_count):
        operator = {"name": f"test_node_operator_{i}", "address": accounts[(i % (len(accounts) - 1)) + 1]}
        add_node_operator_calldata = registry.addNodeOperator.encode_input(operator["name"], operator["address"])
        add_node_operator_evm_script = encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(voting, registry, registry.MANAGE_NODE_OPERATOR_ROLE()),
                ),
                (
                    registry.address,
                    add_node_operator_calldata,
                ),
            ]
        )
        voting_id, _ = lido_contracts.create_voting(
            evm_script=add_node_operator_evm_script,
            description=f"Add node operator {i}",
            tx_params={"from": agent},
        )
        lido_contracts.execute_voting(voting_id)

    # Now, ensure each operator has at least one pubkey
    total_operators = registry.getNodeOperatorsCount()
    for operator_id in range(total_operators):
        operator = registry.getNodeOperator(operator_id, True)
        operator_address = operator[2]
        total_signing_keys = operator[5]
        if total_signing_keys < 1:
            registry.addSigningKeys(
                operator_id,
                1,
                "0x" + pubkeys[0],
                "0x" + signatures[0],
                {"from": operator_address},
            )


def select_first_operator_and_key(registry):
    """Returns (operator_id, pubkey) for the first operator with a signing key."""
    count = registry.getNodeOperatorsCount()
    for operator_id in range(count):
        operator = registry.getNodeOperator(operator_id, True)
        if operator[5] >= 1:
            # You may have to actually query keys, but for test, return our known one
            return operator_id, PUBKEYS[0]
    raise Exception("No operator with at least one signing key found.")


def run_happy_path(
    *,
    factory,
    multisig,
    easy_track,
    validator_exit_bus_oracle,
    exit_requests,
    stranger,
):
    """
    Simulates the full EasyTrack motion happy path for exit requests:
    - Creates the motion and calldata
    - Verifies oracle rejects data before enactment
    - Enacts the motion and verifies RequestsHashSubmitted event
    - Submits the data and checks ValidatorExitRequest events
    """
    from utils.test_helpers import create_exit_request_hash_calldata, create_exit_requests_hashes

    calldata = create_exit_request_hash_calldata([req.to_tuple() for req in exit_requests])

    motion_tx = easy_track.createMotion(
        factory.address,
        calldata,
        {"from": multisig},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1
    motion_id = motions[0][0]
    evm_script_call_data = motion_tx.events["MotionCreated"]["_evmScriptCallData"]

    packed = b"".join(
        [req.to_bytes() if hasattr(req, "to_bytes") else convert.to_bytes(req.to_tuple()) for req in exit_requests]
    )

    with reverts("ExitHashNotSubmitted"):
        validator_exit_bus_oracle.submitExitRequestsData((packed, DATA_FORMAT_LIST), {"from": multisig})

    brownie.chain.sleep(easy_track.motionDuration() + 10)

    enact_tx = easy_track.enactMotion(
        motion_id,
        evm_script_call_data,
        {"from": stranger},
    )

    exit_requests_hash = create_exit_requests_hashes(exit_requests)
    hash_events = enact_tx.events.get("RequestsHashSubmitted", [])
    assert any(
        e["exitRequestsHash"] == exit_requests_hash for e in hash_events
    ), f"RequestsHashSubmitted event for hash {exit_requests_hash.hex()} not found!"

    oracle_tx = validator_exit_bus_oracle.submitExitRequestsData((packed, DATA_FORMAT_LIST), {"from": multisig})
    timestamp = oracle_tx.timestamp
    events = oracle_tx.events["ValidatorExitRequest"]
    assert len(events) == len(exit_requests)
    for idx, req in enumerate(exit_requests):
        event = events[idx]
        assert event["stakingModuleId"] == req.module_id
        assert event["nodeOperatorId"] == req.node_op_id
        assert event["validatorIndex"] == req.val_index
        req_pubkey = req.val_pubkey if isinstance(req.val_pubkey, bytes) else convert.to_bytes(req.val_pubkey, "bytes")
        assert event["validatorPubkey"] == req_pubkey
        assert event["timestamp"] == timestamp


@pytest.mark.parametrize("module", MODULES, ids=[m["name"] for m in MODULES])
def test_evm_script_factory_happy_path(
    module,
    request,
    easy_track,
    lido_contracts,
    validator_exit_bus_oracle,
    exit_request_input_factory,
    stranger,
    accounts,
    submit_exit_hashes_factory_config,
):
    """
    Ensures the registry is filled with 300 operators with at least one signing key, then runs the integration happy path.
    """
    factory = request.getfixturevalue(module["factory_fixture"])
    registry = request.getfixturevalue(module["registry_fixture"])
    multisig = request.getfixturevalue(module["multisig_fixture"])

    voting = lido_contracts.aragon.voting
    agent = lido_contracts.aragon.agent
    acl = lido_contracts.aragon.acl

    ensure_node_operators_and_keys(
        registry=registry,
        lido_contracts=lido_contracts,
        accounts=accounts,
        voting=voting,
        agent=agent,
        acl=acl,
        min_count=300,
    )

    # Find the module id: use config (like in your original tests)
    module_id_key = module["module_id_key"]
    module_id = submit_exit_hashes_factory_config["module_ids"][module_id_key]

    # Pick operator ids and the first pubkey for each
    operator_ids = list(range(registry.getNodeOperatorsCount()))
    pubkeys = [select_first_operator_and_key(registry)[1] for _ in operator_ids]

    # Single request using first operator and pubkey
    single_exit_requests = [
        exit_request_input_factory(
            module_id=module_id,
            node_op_id=operator_ids[0],
            val_index=0,
            val_pubkey=pubkeys[0],
            val_pubkey_index=0,
        )
    ]
    run_happy_path(
        factory=factory,
        multisig=multisig,
        easy_track=easy_track,
        validator_exit_bus_oracle=validator_exit_bus_oracle,
        exit_requests=single_exit_requests,
        stranger=stranger,
    )

    # Batch: one exit request per operator (first 300)
    batch_exit_requests = [
        exit_request_input_factory(
            module_id=module_id,
            node_op_id=operator_id,
            val_index=0,  # could increment if you want, but 0 is fine for all
            val_pubkey=select_first_operator_and_key(registry)[1],  # always first pubkey
            val_pubkey_index=0,
        )
        for operator_id in operator_ids[:300]
    ]
    run_happy_path(
        factory=factory,
        multisig=multisig,
        easy_track=easy_track,
        validator_exit_bus_oracle=validator_exit_bus_oracle,
        exit_requests=batch_exit_requests,
        stranger=stranger,
    )
