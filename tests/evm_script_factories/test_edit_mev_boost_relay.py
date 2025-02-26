import pytest
from eth_abi import encode
from brownie import reverts, EditMEVBoostRelay, web3

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
def edit_mev_boost_relay_factory(owner, mev_boost_relay_allowed_list):
    return EditMEVBoostRelay.deploy(owner, mev_boost_relay_allowed_list, {"from": owner})

def test_deploy(mev_boost_relay_allowed_list, owner, edit_mev_boost_relay_factory):
    "Must deploy contract with correct data"
    assert edit_mev_boost_relay_factory.trustedCaller() == owner
    assert edit_mev_boost_relay_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list

def test_create_evm_script_called_by_stranger(stranger, edit_mev_boost_relay_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        edit_mev_boost_relay_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_relays_count(owner, edit_mev_boost_relay_factory):
    "Must revert with message 'RELAYS_COUNT_MISMATCH' when relays count passed wrong"
    with reverts("RELAYS_COUNT_MISMATCH"):
        CALLDATA = create_calldata(
            [0, [(RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0])]],
        )
        edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_empty_calldata(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = create_calldata([relays_count, []])
        edit_mev_boost_relay_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_empty_relay_uri(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
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
        edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_relay_not_found(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'RELAY_NOT_FOUND' when relay not found"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    with reverts("RELAY_NOT_FOUND"):
        CALLDATA = create_calldata(
            [
                relays_count,
                [
                    (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
                ],
            ]
        )
        edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_one_of_relays_is_not_found(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'RELAY_NOT_FOUND' when one of relays not found"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    with reverts("RELAY_NOT_FOUND"):
        CALLDATA = create_calldata(
            [
                relays_count,
                [
                    (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
                    (RELAY_URIS[1], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
                    (RELAY_URIS[2], OPERATORS[2], IS_MANDATORY[2], DESCRIPTIONS[2]),
                    ("https://relay4.example.com", "Operator 4", True, "Fourth relay description"),
                ],
            ]
        )
        edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_edit_multiple_relays(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must edit multiple relays"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
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
    edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)
    assert mev_boost_relay_allowed_list.get_relays_amount() == 3
    for i in range(3):
        assert mev_boost_relay_allowed_list.get_relay(i) == (
            RELAY_URIS[i],
            OPERATORS[i],
            IS_MANDATORY[i],
            DESCRIPTIONS[i],
        )

def test_create_evm_script(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must create correct EVMScript if all requirements are met"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    CALLDATA = create_calldata(
        [
            relays_count,
            [
                (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
            ],
        ]
    )
    evm_script = edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)
    assert evm_script == encode_call_script(
        [
            {
                "to": mev_boost_relay_allowed_list.address,
                "data": mev_boost_relay_allowed_list.edit_relay.encode_input(
                    RELAY_URIS[0],
                    OPERATORS[0],
                    IS_MANDATORY[0],
                    DESCRIPTIONS[0],
                ),
            },
        ]
    )

def test_create_evm_script_for_multiple_relays(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must create correct EVMScript if all requirements are met"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
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
    evm_script = edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)
    assert evm_script == encode_call_script(
        [
            {
                "to": mev_boost_relay_allowed_list.address,
                "data": mev_boost_relay_allowed_list.edit_relay.encode_input(
                    RELAY_URIS[0],
                    OPERATORS[0],
                    IS_MANDATORY[0],
                    DESCRIPTIONS[0],
                ),
            },
            {
                "to": mev_boost_relay_allowed_list.address,
                "data": mev_boost_relay_allowed_list.edit_relay.encode_input(
                    RELAY_URIS[1],
                    OPERATORS[1],
                    IS_MANDATORY[1],
                    DESCRIPTIONS[1],
                ),
            },
            {
                "to": mev_boost_relay_allowed_list.address,
                "data": mev_boost_relay_allowed_list.edit_relay.encode_input(
                    RELAY_URIS[2],
                    OPERATORS[2],
                    IS_MANDATORY[2],
                    DESCRIPTIONS[2],
                ),
            },
        ]
    )


def test_decode_evm_script_call_data(edit_mev_boost_relay_factory):
    "Must decode EVMScript call data correctly"
    relays_count = 1
    input_params = [
        (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
    ]
    CALLDATA = create_calldata([relays_count, input_params])
    assert edit_mev_boost_relay_factory.decodeEVMScriptCallData(CALLDATA) == (
        relays_count,
        input_params,
    )
    
def test_decode_evm_script_call_data_multiple_relays(edit_mev_boost_relay_factory):
    "Must decode EVMScript call data correctly"
    relays_count = 3
    input_params = [
        (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
        (RELAY_URIS[1], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
        (RELAY_URIS[2], OPERATORS[2], IS_MANDATORY[2], DESCRIPTIONS[2]),
    ]
    CALLDATA = create_calldata([relays_count, input_params])
    assert edit_mev_boost_relay_factory.decodeEVMScriptCallData(CALLDATA) == (
        relays_count,
        input_params,
    )

def test_cannot_edit_multiple_relays_with_error(owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'RELAY_NOT_FOUND' when one of relays not found"
    relays_count = mev_boost_relay_allowed_list.get_relays_amount()
    with reverts("RELAY_NOT_FOUND"):
        CALLDATA = create_calldata(
            [
                relays_count,
                [
                    (RELAY_URIS[0], OPERATORS[0], IS_MANDATORY[0], DESCRIPTIONS[0]),
                    (RELAY_URIS[1], OPERATORS[1], IS_MANDATORY[1], DESCRIPTIONS[1]),
                    (RELAY_URIS[2], OPERATORS[2], IS_MANDATORY[2], DESCRIPTIONS[2]),
                    ("https://relay4.example.com", "Operator 4", True, "Fourth relay description"),
                ],
            ]
        )
        edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)

def test_cannot_edit_relays_with_duplicate_uri(
    owner, edit_mev_boost_relay_factory, mev_boost_relay_allowed_list
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
        edit_mev_boost_relay_factory.createEVMScript(owner, CALLDATA)
