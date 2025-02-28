import pytest
from eth_abi import encode
from brownie import reverts, RemoveMEVBoostRelays

from utils.evm_script import encode_call_script

MAX_RELAY_COUNT = 40
RELAY_FIXTURES = [
    # uri, operator, is_mandatory, description
    ("https://relay1.example.com", "Operator 1", True, "First relay description"),
    ("https://relay2.example.com", "Operator 2", False, "Second relay description"),
    ("https://relay3.example.com", "Operator 3", True, "Third relay description"),
]


def create_calldata(data):
    return (
        "0x"
        + encode(
            ["string[]"],
            [data],
        ).hex()
    )


def get_relay_fixture_uri(index):
    return RELAY_FIXTURES[index][0]


def get_max_relay_count(mev_boost_relay_allowed_list):
    current_relay_count = mev_boost_relay_allowed_list.get_relays_amount()

    return MAX_RELAY_COUNT - current_relay_count


@pytest.fixture(scope="module")
def remove_mev_boost_relays_factory(owner, mev_boost_relay_allowed_list):
    return RemoveMEVBoostRelays.deploy(owner, mev_boost_relay_allowed_list, {"from": owner})


def test_deploy(mev_boost_relay_allowed_list, owner, remove_mev_boost_relays_factory):
    "Must deploy contract with correct data"
    assert remove_mev_boost_relays_factory.trustedCaller() == owner
    assert remove_mev_boost_relays_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list


def test_decode_evm_script_call_data_with_single_relay(remove_mev_boost_relays_factory):
    "Must decode EVMScript call data correctly when removing a single relay"
    input_uri = get_relay_fixture_uri(0)
    EVM_SCRIPT_CALLDATA = create_calldata([input_uri])

    decoded_uris = remove_mev_boost_relays_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_uris == [input_uri]


def test_decode_evm_script_call_data_with_multiple_relays(remove_mev_boost_relays_factory):
    "Must decode EVMScript call data correctly"
    input_uris = [get_relay_fixture_uri(0), get_relay_fixture_uri(1)]
    EVM_SCRIPT_CALLDATA = create_calldata(input_uris)

    decoded_uris = remove_mev_boost_relays_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_uris == input_uris


def test_decode_evm_script_call_data_with_max_relays(remove_mev_boost_relays_factory):
    "Must decode EVMScript call data correctly when removing max relays"
    input_uris = [f"https://relay{i}.example.com" for i in range(0, 40)]

    decoded_uris = remove_mev_boost_relays_factory.decodeEVMScriptCallData(create_calldata(input_uris))
    assert decoded_uris == input_uris


def test_decode_evm_script_call_data_with_empty_calldata(remove_mev_boost_relays_factory):
    "Must decode EVMScript call data correctly when removing max relays"
    with reverts():
        remove_mev_boost_relays_factory.decodeEVMScriptCallData("0x")


def test_remove_relay(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must remove relay if it exists"
    # First add a relay that we'll then remove
    mev_boost_relay_allowed_list.add_relay(*RELAY_FIXTURES[0], {"from": owner})

    # Create script to remove the relay
    evm_script = remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata([get_relay_fixture_uri(0)]))

    # Create expected script
    expected_evm_script = encode_call_script(
        [
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.remove_relay.encode_input(get_relay_fixture_uri(0)),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_remove_multiple_relays(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must remove all relays if they exist"
    # First add relays that we'll then remove
    inputs = []
    direct_allow_list_calldata = []

    for i in range(4):
        relay_uri = f"uri{i}"

        mev_boost_relay_allowed_list.add_relay(
            relay_uri,
            f"operator{i}",
            True,
            f"description{i}",
            {"from": owner},
        )

        inputs.append(relay_uri)
        direct_allow_list_calldata.append(
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.remove_relay.encode_input(
                    relay_uri,
                ),
            )
        )

    calldata = create_calldata(inputs)
    evm_script = remove_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_remove_max_num_relays(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must remove max relays if they exist"
    # First add relays that we'll then remove
    inputs = []
    direct_allow_list_calldata = []

    for i in range(get_max_relay_count(mev_boost_relay_allowed_list)):
        relay_uri = f"uri{i}"

        mev_boost_relay_allowed_list.add_relay(
            relay_uri,
            f"operator{i}",
            True,
            f"description{i}",
            {"from": owner},
        )

        inputs.append(relay_uri)
        direct_allow_list_calldata.append(
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.remove_relay.encode_input(
                    relay_uri,
                ),
            )
        )

    calldata = create_calldata(inputs)
    evm_script = remove_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_cannot_create_evm_script_called_by_stranger(stranger, remove_mev_boost_relays_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        remove_mev_boost_relays_factory.createEVMScript(stranger, "0x")


def test_cannot_remove_relay_with_empty_calldata(owner, remove_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_CALLDATA' when no URIs provided"
    with reverts("EMPTY_CALLDATA"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata([]))


def test_cannot_remove_relay_with_empty_relay_uri(owner, remove_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_RELAY_URI' when uri is empty"
    with reverts("EMPTY_RELAY_URI"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata([""]))


def test_cannot_remove_more_than_available(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'REMOVING_MORE_RELAYS_THAN_AVAILABLE' when trying to remove more relays than exist"
    current_relay_count = mev_boost_relay_allowed_list.get_relays_amount()

    # Create array of URIs that is larger than the current relay count
    uris_to_remove = []
    for i in range(current_relay_count + 1):  # One more than exists
        uris_to_remove.append(f"https://relay{i}.example.com")

    with reverts("REMOVING_MORE_RELAYS_THAN_AVAILABLE"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata(uris_to_remove))


def test_cannot_remove_more_than_max(
    owner,
    remove_mev_boost_relays_factory,
):
    "Must revert with message 'REMOVING_MORE_RELAYS_THAN_AVAILABLE' when trying to remove more relays than allowed"
    # Create array of URIs that is larger than the max relay count
    uris_to_remove = []
    for i in range(MAX_RELAY_COUNT + 1):  # One more than allowed
        uris_to_remove.append(f"https://relay{i}.example.com")

    with reverts("REMOVING_MORE_RELAYS_THAN_AVAILABLE"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata(uris_to_remove))


def test_cannot_remove_relay_uri_not_in_list(owner, remove_mev_boost_relays_factory):
    "Must revert with message 'RELAY_URI_NOT_IN_LIST' when trying to remove relay that doesn't exist"
    # Try to remove a relay that doesn't exist
    with reverts("NO_RELAY_WITH_GIVEN_URI"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata([get_relay_fixture_uri(0)]))


def test_cannot_remove_relays_with_duplicate_uri(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'DUPLICATE_RELAY_URI' when trying to remove two relays with the same URI"

    # Add a relay
    mev_boost_relay_allowed_list.add_relay(*RELAY_FIXTURES[0], {"from": owner})

    with reverts("DUPLICATE_RELAY_URI"):
        remove_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    get_relay_fixture_uri(0),
                    get_relay_fixture_uri(0),
                ]
            ),
        )
