import pytest
from eth_abi import encode
from brownie import reverts, EditMEVBoostRelays

from utils.evm_script import encode_call_script

MAX_STRING_LENGTH = 1024
MAX_RELAY_COUNT = 40
RELAY_FIXTURES = [
    # uri, operator, is_mandatory, description
    ("https://relay1.example.com", "Operator 1", True, "First relay description"),
    ("https://relay2.example.com", "Operator 2", False, "Second relay description"),
    ("https://relay3.example.com", "Operator 3", True, "Third relay description"),
]


def create_calldata(data):
    return "0x" + encode(["(string,string,bool,string)[]"], [data]).hex()


def get_relay_fixture_uri(index):
    return RELAY_FIXTURES[index][0]


def get_max_relay_count(mev_boost_relay_allowed_list):
    current_relay_count = mev_boost_relay_allowed_list.get_relays_amount()

    return MAX_RELAY_COUNT - current_relay_count


@pytest.fixture(scope="module")
def edit_mev_boost_relays_factory(owner, mev_boost_relay_allowed_list):
    return EditMEVBoostRelays.deploy(owner, mev_boost_relay_allowed_list, {"from": owner})


def test_deploy(mev_boost_relay_allowed_list, owner, edit_mev_boost_relays_factory):
    "Must deploy contract with correct data"
    assert edit_mev_boost_relays_factory.trustedCaller() == owner
    assert edit_mev_boost_relays_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list


def test_decode_evm_script_call_data_single_relay(edit_mev_boost_relays_factory):
    "Must decode EVMScript call data correctly"
    input_params = [RELAY_FIXTURES[0]]
    calldata = create_calldata(input_params)

    assert edit_mev_boost_relays_factory.decodeEVMScriptCallData(calldata) == (RELAY_FIXTURES[0],)


def test_decode_evm_script_call_data_multiple_relays(edit_mev_boost_relays_factory):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(RELAY_FIXTURES)
    assert edit_mev_boost_relays_factory.decodeEVMScriptCallData(calldata) == RELAY_FIXTURES


def test_edit_single_relay(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must edit single relay"
    input_params = [RELAY_FIXTURES[0]]

    mev_boost_relay_allowed_list.add_relay(*input_params[0], {"from": owner})

    calldata = create_calldata(input_params)
    direct_allow_list_calldata = [
        (
            mev_boost_relay_allowed_list.address,
            mev_boost_relay_allowed_list.remove_relay.encode_input(
                get_relay_fixture_uri(0),
            ),
        ),
        (
            mev_boost_relay_allowed_list.address,
            mev_boost_relay_allowed_list.add_relay.encode_input(
                *input_params[0],
            ),
        ),
    ]

    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)
    expected_evm_script = encode_call_script(direct_allow_list_calldata)

    assert evm_script == expected_evm_script


def test_edit_multiple_relays(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must edit multiple relays"
    calldata = create_calldata(RELAY_FIXTURES)
    direct_allow_list_calldata = []

    for relay in RELAY_FIXTURES:
        mev_boost_relay_allowed_list.add_relay(*relay, {"from": owner})

        direct_allow_list_calldata += [
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.remove_relay.encode_input(relay[0]),
            ),
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.add_relay.encode_input(
                    *relay,
                ),
            ),
        ]

    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)
    expected_evm_script = encode_call_script(direct_allow_list_calldata)

    assert evm_script == expected_evm_script


def test_edit_max_num_relays(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must add the last relay if the number of relays is less than MAX_NUM_RELAYS"

    inputs = []
    direct_allow_list_calldata = []

    for i in range(get_max_relay_count(mev_boost_relay_allowed_list)):
        relay = (f"uri{i}", f"operator{i}", True, f"description{i}")

        mev_boost_relay_allowed_list.add_relay(*relay, {"from": owner})

        inputs.append(relay)
        direct_allow_list_calldata += [
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.remove_relay.encode_input(relay[0]),
            ),
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.add_relay.encode_input(
                    *relay,
                ),
            ),
        ]

    calldata = create_calldata(inputs)
    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_can_edit_relay_and_set_description_to_empty(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list
):
    "Must edit relay with empty description"
    input_params = [RELAY_FIXTURES[0][:3] + ("",)]
    mev_boost_relay_allowed_list.add_relay(*RELAY_FIXTURES[0], {"from": owner})

    calldata = create_calldata(input_params)
    direct_allow_list_calldata = [
        (
            mev_boost_relay_allowed_list.address,
            mev_boost_relay_allowed_list.remove_relay.encode_input(
                get_relay_fixture_uri(0),
            ),
        ),
        (
            mev_boost_relay_allowed_list.address,
            mev_boost_relay_allowed_list.add_relay.encode_input(
                *input_params[0],
            ),
        ),
    ]

    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)
    expected_evm_script = encode_call_script(direct_allow_list_calldata)

    assert evm_script == expected_evm_script


def test_can_edit_relay_and_set_operator_to_empty(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must edit relay with empty operator"
    input_params = [("",) + RELAY_FIXTURES[0][1:]]
    mev_boost_relay_allowed_list.add_relay(*RELAY_FIXTURES[0], {"from": owner})

    calldata = create_calldata(input_params)
    direct_allow_list_calldata = [
        (
            mev_boost_relay_allowed_list.address,
            mev_boost_relay_allowed_list.remove_relay.encode_input(
                get_relay_fixture_uri(0),
            ),
        ),
        (
            mev_boost_relay_allowed_list.address,
            mev_boost_relay_allowed_list.add_relay.encode_input(
                *input_params[0],
            ),
        ),
    ]

    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)
    expected_evm_script = encode_call_script(direct_allow_list_calldata)

    assert evm_script == expected_evm_script


def test_cannot_decode_evm_script_call_data_with_empty_calldata(edit_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_RELAYS_ARRAY' when calldata is empty"
    with reverts():
        edit_mev_boost_relays_factory.decodeEVMScriptCallData("0x")


def test_cannot_create_evm_script_called_by_stranger(stranger, edit_mev_boost_relays_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        edit_mev_boost_relays_factory.createEVMScript(stranger, "0x")


def test_cannot_edit_relay_with_empty_calldata(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'EMPTY_RELAYS_ARRAY' when calldata is empty"
    with reverts("EMPTY_RELAYS_ARRAY"):
        edit_mev_boost_relays_factory.createEVMScript(owner, create_calldata([]))


def test_cannot_edit_relay_with_empty_uri(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'EMPTY_RELAY_URI' when uri is empty"
    with reverts("EMPTY_RELAY_URI"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    ("", "operator", True, "description"),
                ]
            ),
        )


def test_cannot_edit_relay_with_duplicate_uri(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'DUPLICATE_RELAY_URI' when uri is duplicated"
    relays = [
        (get_relay_fixture_uri(0), "operator 1", True, "description 1"),
        (get_relay_fixture_uri(0), "operator 2", False, "description 2"),
    ]

    mev_boost_relay_allowed_list.add_relay(*relays[0], {"from": owner})

    with reverts("DUPLICATE_RELAY_URI"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(relays),
        )


def test_cannot_edit_more_relays_than_present(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'RELAY_NOT_FOUND' when trying to add more relays than MAX_RELAY_COUNT"
    current_relay_count = mev_boost_relay_allowed_list.get_relays_amount()

    # Ensure that the current relay count is within the allowed range
    assert current_relay_count > 0 and current_relay_count < MAX_RELAY_COUNT

    with reverts("RELAY_NOT_FOUND"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                # here it doesn't matter that URI doesn't exist in the allow list, we're testing the count mismatch here only
                # checks for URI existence in the allow list are covered in other tests
                [(f"uri{i}", f"operator{i}", True, f"description{i}") for i in range(current_relay_count + 1)]
            ),
        )


def test_cannot_edit_relay_not_in_allow_list(owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'RELAY_NOT_FOUND' when relay is not in the allow list"
    with reverts("RELAY_NOT_FOUND"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata([RELAY_FIXTURES[0]]),
        )


def test_cannot_edit_relay_not_in_allow_list_with_multiple_relays(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list
):
    "Must revert with message 'RELAY_NOT_FOUND' when relay is not in the allow list"
    # Add one relay to the allow list
    mev_boost_relay_allowed_list.add_relay(*RELAY_FIXTURES[0], {"from": owner})

    # Try to edit two relays, one of them is not in the allow list
    with reverts("RELAY_NOT_FOUND"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(RELAY_FIXTURES[:2]),
        )


def test_cannot_edit_relay_with_operator_over_max_string_length(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list
):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when operator is over max string length"
    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    (f"uri{i}", "o" * (MAX_STRING_LENGTH + 1), True, f"description{i}")
                    for i in range(get_max_relay_count(mev_boost_relay_allowed_list))
                ]
            ),
        )


def test_cannot_edit_relay_with_description_over_max_string_length(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list
):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when description is over max string length"
    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    (f"uri{i}", f"operator{i}", True, "d" * (MAX_STRING_LENGTH + 1))
                    for i in range(get_max_relay_count(mev_boost_relay_allowed_list))
                ]
            ),
        )
