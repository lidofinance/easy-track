import pytest
from eth_abi import encode
from brownie import reverts, RemoveMEVBoostRelays

from utils.evm_script import encode_call_script


def create_calldata(data):
    return (
        "0x"
        + encode(
            ["string[]"],
            [data],
        ).hex()
    )


def get_relay_fixture_uri(i, mev_boost_relay_test_config):
    return mev_boost_relay_test_config["relays"][i][0]


@pytest.fixture(scope="module")
def remove_mev_boost_relays_factory(owner, mev_boost_relay_allowed_list_stub):
    return RemoveMEVBoostRelays.deploy(owner, mev_boost_relay_allowed_list_stub, {"from": owner})


def test_deploy(mev_boost_relay_allowed_list_stub, owner, remove_mev_boost_relays_factory):
    "Must deploy contract with correct data"
    assert remove_mev_boost_relays_factory.trustedCaller() == owner
    assert remove_mev_boost_relays_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list_stub


def test_decode_evm_script_call_data_with_single_relay(remove_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly when removing a single relay"
    input_uri = get_relay_fixture_uri(0, mev_boost_relay_test_config)
    EVM_SCRIPT_CALLDATA = create_calldata([input_uri])

    decoded_uris = remove_mev_boost_relays_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_uris == [input_uri]


def test_decode_evm_script_call_data_with_multiple_relays(remove_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly"
    input_uris = [
        get_relay_fixture_uri(0, mev_boost_relay_test_config),
        get_relay_fixture_uri(1, mev_boost_relay_test_config),
    ]
    EVM_SCRIPT_CALLDATA = create_calldata(input_uris)

    decoded_uris = remove_mev_boost_relays_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_uris == input_uris


def test_decode_evm_script_call_data_with_max_relays(remove_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly when removing max relays"
    input_uris = [f"https://relay{i}.example.com" for i in range(0, mev_boost_relay_test_config["max_num_relays"])]

    decoded_uris = remove_mev_boost_relays_factory.decodeEVMScriptCallData(create_calldata(input_uris))
    assert decoded_uris == input_uris


def test_decode_evm_script_call_data_with_empty_calldata(remove_mev_boost_relays_factory):
    "Must revert on decoding EVMScript call data with empty calldata"
    with reverts():
        remove_mev_boost_relays_factory.decodeEVMScriptCallData("0x")


def test_remove_relay(
    owner, remove_mev_boost_relays_factory, mev_boost_relay_test_config, mev_boost_relay_allowed_list_stub
):
    "Must remove relay if it exists"
    # First add a relay that we'll then remove
    mev_boost_relay_allowed_list_stub.add_relay(*mev_boost_relay_test_config["relays"][0], {"from": owner})
    assert mev_boost_relay_allowed_list_stub.get_relays_amount() == 1

    # Create script to remove the relay
    evm_script = remove_mev_boost_relays_factory.createEVMScript(
        owner, create_calldata([get_relay_fixture_uri(0, mev_boost_relay_test_config)])
    )

    # Create expected script
    expected_evm_script = encode_call_script(
        [
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.remove_relay.encode_input(
                    get_relay_fixture_uri(0, mev_boost_relay_test_config)
                ),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_remove_multiple_relays(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub):
    "Must remove all relays if they exist"
    # First add relays that we'll then remove
    inputs = []
    direct_allow_list_calldata = []

    # Add a relay that we'll keep for better semantics in tests as we're not removing all relays
    mev_boost_relay_allowed_list_stub.add_relay("uri0", "operator0", True, "description0", {"from": owner})

    for i in range(4):
        relay_uri = f"uri{i}"

        mev_boost_relay_allowed_list_stub.add_relay(
            relay_uri,
            f"operator{i}",
            True,
            f"description{i}",
            {"from": owner},
        )

        inputs.append(relay_uri)
        direct_allow_list_calldata.append(
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.remove_relay.encode_input(
                    relay_uri,
                ),
            )
        )

    assert mev_boost_relay_allowed_list_stub.get_relays_amount() == len(inputs) + 1

    calldata = create_calldata(inputs)
    evm_script = remove_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_remove_max_num_relays(
    owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must remove max relays if they exist"
    # First add relays that we'll then remove
    inputs = []
    direct_allow_list_calldata = []

    current_relay_count = mev_boost_relay_allowed_list_stub.get_relays_amount()
    max_count = mev_boost_relay_test_config["max_num_relays"] - current_relay_count

    for i in range(max_count):
        relay_uri = f"uri{i}"

        mev_boost_relay_allowed_list_stub.add_relay(
            relay_uri,
            f"operator{i}",
            True,
            f"description{i}",
            {"from": owner},
        )

        inputs.append(relay_uri)
        direct_allow_list_calldata.append(
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.remove_relay.encode_input(
                    relay_uri,
                ),
            )
        )

    assert mev_boost_relay_allowed_list_stub.get_relays_amount() == max_count

    calldata = create_calldata(inputs)
    evm_script = remove_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_can_remove_all_relays_in_allow_list(
    owner, remove_mev_boost_relays_factory, mev_boost_relay_test_config, mev_boost_relay_allowed_list_stub
):
    "Must remove all relays in the allow list"
    # First add relays that we'll then remove
    inputs = []
    direct_allow_list_calldata = []

    for i in range(len(mev_boost_relay_test_config["relays"])):
        relay_uri = get_relay_fixture_uri(i, mev_boost_relay_test_config)

        mev_boost_relay_allowed_list_stub.add_relay(
            relay_uri,
            f"operator{i}",
            True,
            f"description{i}",
            {"from": owner},
        )

        inputs.append(relay_uri)
        direct_allow_list_calldata.append(
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.remove_relay.encode_input(
                    relay_uri,
                ),
            )
        )

    assert mev_boost_relay_allowed_list_stub.get_relays_amount() == len(mev_boost_relay_test_config["relays"])

    calldata = create_calldata(inputs)
    evm_script = remove_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_cannot_create_evm_script_called_by_stranger(stranger, remove_mev_boost_relays_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        remove_mev_boost_relays_factory.createEVMScript(stranger, "0x")


def test_cannot_remove_relay_with_empty_calldata(owner, remove_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_RELAYS_ARRAY' when no URIs provided"
    with reverts("EMPTY_RELAYS_ARRAY"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata([]))


def test_cannot_remove_relay_with_empty_relay_uri(owner, remove_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_RELAY_URI' when uri is empty"
    with reverts("EMPTY_RELAY_URI"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata([""]))


def test_cannot_edit_multiple_relays_when_last_not_in_allow_list(
    owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub
):
    "Must revert with message 'RELAY_NOT_FOUND' when trying to remove more relays than exist"
    current_relay_count = mev_boost_relay_allowed_list_stub.get_relays_amount()

    # Create array of URIs that is larger than the current relay count
    uris_to_remove = []
    for i in range(current_relay_count + 1):  # One more than exists
        uris_to_remove.append(f"https://relay{i}.example.com")

    with reverts("RELAY_NOT_FOUND"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata(uris_to_remove))


def test_cannot_remove_more_than_max(owner, remove_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must revert with message 'RELAY_NOT_FOUND' when trying to remove more relays than allowed"
    # Create array of URIs that is larger than the max relay count
    uris_to_remove = []
    for i in range(mev_boost_relay_test_config["max_num_relays"] + 1):  # One more than allowed
        uris_to_remove.append(f"https://relay{i}.example.com")

    with reverts("RELAY_NOT_FOUND"):
        remove_mev_boost_relays_factory.createEVMScript(owner, create_calldata(uris_to_remove))


def test_cannot_remove_relay_uri_not_in_list(owner, remove_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must revert with message 'RELAY_NOT_FOUND' when trying to remove relay that doesn't exist"
    # Try to remove a relay that doesn't exist
    with reverts("RELAY_NOT_FOUND"):
        remove_mev_boost_relays_factory.createEVMScript(
            owner, create_calldata([get_relay_fixture_uri(0, mev_boost_relay_test_config)])
        )


def test_cannot_remove_relays_with_duplicate_uri(
    owner, remove_mev_boost_relays_factory, mev_boost_relay_test_config, mev_boost_relay_allowed_list_stub
):
    "Must revert with message 'DUPLICATE_RELAY_URI' when trying to remove two relays with the same URI"

    # Add a relay
    mev_boost_relay_allowed_list_stub.add_relay(*mev_boost_relay_test_config["relays"][0], {"from": owner})

    assert mev_boost_relay_allowed_list_stub.get_relays_amount() == 1

    with reverts("DUPLICATE_RELAY_URI"):
        remove_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    get_relay_fixture_uri(0, mev_boost_relay_test_config),
                    get_relay_fixture_uri(0, mev_boost_relay_test_config),
                ]
            ),
        )
