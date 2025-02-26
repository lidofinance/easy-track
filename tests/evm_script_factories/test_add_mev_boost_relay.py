import pytest
from eth_abi import encode
from brownie import reverts, AddMEVBoostRelay, web3

from utils.evm_script import encode_call_script

RELAY_URIS = [
    "https://relay1.example.com",
    "https://relay2.example.com",
    "https://relay3.example.com",
]

OPERATORS = [
    "Operator 1",
    "Operator 2",
    "Operator 3",
]

IS_MANDATORY = [
    True,
    False,
    True,
]

DESCRIPTIONS = [
    "First relay description",
    "Second relay description",
    "Third relay description",
]

def create_calldata(data):
    return (
        "0x"
        + encode(
            ["uint256", "(string,string,bool,string)[]"],
            data,
        ).hex()
    )

@pytest.fixture(scope="module")
def add_mev_boost_relay_factory(owner, mev_boost_relay_allowed_list):
    return AddMEVBoostRelay.deploy(owner, mev_boost_relay_allowed_list, {"from": owner})

def test_deploy(mev_boost_relay_allowed_list, owner, add_mev_boost_relay_factory):
    "Must deploy contract with correct data"
    assert add_mev_boost_relay_factory.trustedCaller() == owner
    assert add_mev_boost_relay_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list

def test_create_evm_script_called_by_stranger(stranger, add_mev_boost_relay_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        add_mev_boost_relay_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_relays_count_mismatch(owner, add_mev_boost_relay_factory):
    "Must revert with message 'RELAYS_COUNT_MISMATCH' when relays count passed wrong"
    with reverts("RELAYS_COUNT_MISMATCH"):
        CALLDATA = create_calldata(
            [0, [(RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0])]],
        )
        add_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)
        
def test_empty_calldata(owner, add_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = create_calldata([relays_count, []])
        add_mev_boost_relay_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_empty_relay_uri(owner, add_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'EMPTY_RELAY_URI' when uri is empty"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    with reverts("EMPTY_RELAY_URI"):
        CALLDATA = create_calldata(
            [
                relays_count,
                [
                    ("", OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
                ],
            ]
        )
        add_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_max_num_relays_exceeded(owner, add_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'MAX_NUM_RELAYS_EXCEEDED' when too many relays are being added"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()

    # Create array of 41 relay inputs (exceeding MAX_NUM_RELAYS of 40)
    inputs = []
    for i in range(41):
        inputs.append((f"uri{i}", f"operator{i}", True, f"description{i}"))

    with reverts("MAX_NUM_RELAYS_EXCEEDED"):
        CALLDATA = create_calldata([relays_count, inputs])
        add_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_relay_uri_already_exists(
    owner, add_mev_boost_relay_factory, mev_boost_relay_allowed_list
):
    "Must revert with message 'RELAY_URI_ALREADY_EXISTS' when uri already exists in allowed list"

    # First add a relay
    mev_boost_relay_allowed_list.add_relay(
        RELAY_URIS[0],
        OPERATORS[0],
        IS_MANDATORY[0],
        DESCRIPTIONS[0],
        {"from": owner}
    )

    added_relay = mev_boost_relay_allowed_list.get_relay_by_uri(RELAY_URIS[0])
    assert added_relay[0] == RELAY_URIS[0]
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()

    # Try to add the same URI again
    with reverts("RELAY_URI_ALREADY_EXISTS"):
        CALLDATA = create_calldata(
            [
                relays_count,
                [
                    (RELAY_URIS[0], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
                ],
            ]
        )
        add_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, add_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must create correct EVMScript if all requirements are met"

    input_params = [
        (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
        (RELAY_URIS[1], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
    ]

    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    CALLDATA = create_calldata([relays_count, input_params])

    evm_script = add_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

    scripts = []
    for input_param in input_params:
        scripts.append(
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.add_relay.encode_input(
                    input_param[0],  # uri
                    input_param[1],  # operator
                    input_param[2],  # is_mandatory
                    input_param[3],  # description
                ),
            )
        )

    expected_evm_script = encode_call_script(scripts)
    assert evm_script == expected_evm_script

def test_cannot_batch_create_evm_scripts_with_error( owner, add_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'RELAY_URI_ALREADY_EXISTS' when uri of one of the relays already exists in allowed list"

    # First add a relay
    mev_boost_relay_allowed_list.add_relay(
        RELAY_URIS[1],
        OPERATORS[1],
        IS_MANDATORY[1],
        DESCRIPTIONS[1],
        {"from": owner}
    )

    added_relay = mev_boost_relay_allowed_list.get_relay_by_uri(RELAY_URIS[0])
    assert added_relay[0] == RELAY_URIS[0]
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()

    # Try to add the same URI again
    with reverts("RELAY_URI_ALREADY_EXISTS"):
        CALLDATA = create_calldata(
            [
                relays_count,
                [
                    (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
                    (RELAY_URIS[1], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
                    (RELAY_URIS[2], OPERATORS[2], IS_MANDATORY[2], DESCRIPTIONS[2]),
                ],
            ]
        )
        add_mev_boost_relay_factory.batchCreateEVMScripts(owner, [CALLDATA, CALLDATA])

def test_decode_evm_script_call_data(mev_boost_relay_allowed_list, add_mev_boost_relay_factory):
    "Must decode EVMScript call data correctly"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    input_params = [
        relays_count,
        [
            (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
            (RELAY_URIS[1], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
        ],
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    assert add_mev_boost_relay_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params

def test_cannot_add_relays_with_duplicate_uri(
    owner, add_mev_boost_relay_factory, mev_boost_relay_allowed_list
):
    "Must revert with message 'RELAY_URI_HAS_A_DUPLICATE' when trying to add two relays with the same URI"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()

    assert relays_count == 0

    # Create array of 2 relay inputs with the same URI
    inputs = [
        (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
        (RELAY_URIS[0], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
    ]

    with reverts("RELAY_URI_HAS_A_DUPLICATE"):
        CALLDATA = create_calldata([relays_count, inputs])
        add_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)
