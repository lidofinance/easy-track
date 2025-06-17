import pytest
from eth_abi import encode
from brownie import reverts, AddMEVBoostRelays

from utils.evm_script import encode_call_script


def create_calldata(data):
    return "0x" + encode(["(string,string,bool,string)[]"], [data]).hex()


@pytest.fixture(scope="module")
def add_mev_boost_relays_factory(owner, mev_boost_relay_allowed_list_stub):
    return AddMEVBoostRelays.deploy(owner, mev_boost_relay_allowed_list_stub, {"from": owner})


def test_deploy(mev_boost_relay_allowed_list_stub, owner, add_mev_boost_relays_factory):
    "Must deploy contract with correct data"
    assert add_mev_boost_relays_factory.trustedCaller() == owner
    assert add_mev_boost_relays_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list_stub


def test_decode_evm_script_call_data_with_single_relay(add_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly when adding a single relay"
    input_params = [mev_boost_relay_test_config["relays"][0]]
    calldata = create_calldata(input_params)

    assert add_mev_boost_relays_factory.decodeEVMScriptCallData(calldata) == input_params


def test_decode_evm_script_call_data_multiple_relays(add_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly"
    input_params = [
        mev_boost_relay_test_config["relays"][0],
        mev_boost_relay_test_config["relays"][1],
    ]
    calldata = create_calldata(input_params)

    assert add_mev_boost_relays_factory.decodeEVMScriptCallData(calldata) == input_params


def test_decode_evm_script_call_data_with_max_relays(add_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly when adding the maximum number of relays"
    input_params = []
    for i in range(mev_boost_relay_test_config["max_num_relays"]):
        input_params.append((f"uri{i}", f"operator{i}", True, f"description{i}"))

    calldata = create_calldata(input_params)

    assert add_mev_boost_relays_factory.decodeEVMScriptCallData(calldata) == input_params


def test_decode_evm_script_call_data_reverts_with_empty_calldata(add_mev_boost_relays_factory):
    "Must revert on decoding EVMScript call data with empty calldata"
    with reverts():
        add_mev_boost_relays_factory.decodeEVMScriptCallData("0x")


def test_create_evm_script_with_one_relay(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must create correct EVMScript when adding one relay"
    evm_script = add_mev_boost_relays_factory.createEVMScript(
        owner, create_calldata([mev_boost_relay_test_config["relays"][0]])
    )

    direct_allow_list_calldata = [
        (
            mev_boost_relay_allowed_list_stub.address,
            mev_boost_relay_allowed_list_stub.add_relay.encode_input(
                *mev_boost_relay_test_config["relays"][0],
            ),
        )
    ]

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_create_evm_script_with_multiple_relays(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must create correct EVMScript when adding multiple relays"
    evm_script = add_mev_boost_relays_factory.createEVMScript(
        owner,
        create_calldata(mev_boost_relay_test_config["relays"]),
    )

    direct_allow_list_calldata = []
    for i in range(len(mev_boost_relay_test_config["relays"])):
        direct_allow_list_calldata.append(
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.add_relay.encode_input(
                    *mev_boost_relay_test_config["relays"][i],
                ),
            )
        )

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_add_max_num_relays(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must add the last relay if the number of relays is less than MAX_NUM_RELAYS"
    inputs = []
    direct_allow_list_calldata = []

    # create array of relays to reach the limit
    for i in range(mev_boost_relay_test_config["max_num_relays"]):
        relay = (f"uri{i}", f"operator{i}", True, f"description{i}")
        inputs.append(relay)
        direct_allow_list_calldata.append(
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.add_relay.encode_input(*relay),
            )
        )

    calldata = create_calldata(inputs)
    evm_script = add_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_cannot_create_evm_script_called_by_stranger(stranger, add_mev_boost_relays_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        add_mev_boost_relays_factory.createEVMScript(stranger, "0x")


def test_cannot_add_relay_with_empty_calldata(owner, add_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_RELAYS_ARRAY' when no сalldata provided"
    with reverts("EMPTY_RELAYS_ARRAY"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([]))


def test_cannot_add_relay_with_empty_relay_uri(owner, add_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_RELAY_URI' when uri is empty"
    with reverts("EMPTY_RELAY_URI"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([("", "operator", True, "description")]))


def test_cannot_add_more_relays_than_allowed(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must revert with message 'MAX_NUM_RELAYS_EXCEEDED' when too many relays are being added"
    # create array of relays to reach the limit
    for i in range(mev_boost_relay_test_config["max_num_relays"]):
        mev_boost_relay_allowed_list_stub.add_relay(f"uri{i}", f"operator{i}", True, f"description{i}", {"from": owner})

    with reverts("MAX_NUM_RELAYS_EXCEEDED"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([mev_boost_relay_test_config["relays"][0]]))


def test_cannot_batch_add_more_relays_than_allowed(owner, add_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must revert with message 'MAX_NUM_RELAYS_EXCEEDED' when too many relays are being added"
    # Create array of 41 relay inputs (exceeding MAX_NUM_RELAYS of 40)
    inputs = []
    for i in range(mev_boost_relay_test_config["max_num_relays"] + 1):
        inputs.append((f"uri{i}", f"operator{i}", True, f"description{i}"))

    with reverts("MAX_NUM_RELAYS_EXCEEDED"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata(inputs))


def test_cannot_add_relay_uri_already_exists(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must revert with message 'RELAY_URI_ALREADY_EXISTS' when uri already exists in allowed list"
    # First add a relay
    mev_boost_relay_allowed_list_stub.add_relay(*mev_boost_relay_test_config["relays"][0], {"from": owner})

    assert mev_boost_relay_allowed_list_stub.get_relays_amount() == 1

    added_relay = mev_boost_relay_allowed_list_stub.get_relay_by_uri(mev_boost_relay_test_config["relays"][0][0])
    assert added_relay[0] == mev_boost_relay_test_config["relays"][0][0]

    # Try to add the same URI again
    with reverts("RELAY_URI_ALREADY_EXISTS"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([mev_boost_relay_test_config["relays"][0]]))


def test_cannot_add_relays_with_duplicate_uri(owner, add_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must revert with message 'DUPLICATE_RELAY_URI' when trying to add two relays with the same URI"
    fixture = mev_boost_relay_test_config["relays"][0]
    second_fixture = mev_boost_relay_test_config["relays"][1]

    # Create array of 2 relay inputs with the same URI
    inputs = [
        fixture,
        (fixture[0], second_fixture[1], second_fixture[2], second_fixture[3]),
    ]

    with reverts("DUPLICATE_RELAY_URI"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata(inputs))


def test_can_add_relay_with_max_uri_length(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must add relay with URI length"
    uri = "a" * mev_boost_relay_test_config["max_string_length"]

    calldata = create_calldata([(uri, "operator", True, "description")])
    evm_script = add_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.add_relay.encode_input(uri, "operator", True, "description"),
            )
        ]
    )

    assert evm_script == expected_evm_script
    add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([(uri, "operator", True, "description")]))


def test_can_add_relay_with_max_string_length_description(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must add relay with description length"
    description = "a" * mev_boost_relay_test_config["max_string_length"]

    calldata = create_calldata([("uri", "operator", True, description)])
    evm_script = add_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.add_relay.encode_input("uri", "operator", True, description),
            )
        ]
    )

    assert evm_script == expected_evm_script
    add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([("uri", "operator", True, description)]))


def test_can_add_relay_with_max_string_length_operator(
    owner, add_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must add relay with operator length"
    operator = "a" * mev_boost_relay_test_config["max_string_length"]

    calldata = create_calldata([("uri", operator, True, "description")])
    evm_script = add_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.add_relay.encode_input("uri", operator, True, "description"),
            )
        ]
    )

    assert evm_script == expected_evm_script
    add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([("uri", operator, True, "description")]))


def test_cannot_add_relay_with_over_max_string_length_description(
    owner, add_mev_boost_relays_factory, mev_boost_relay_test_config
):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when description is longer than 255 characters"
    description = "a" * (mev_boost_relay_test_config["max_string_length"] + 1)

    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([("uri", "operator", True, description)]))


def test_cannot_add_relay_with_over_max_string_length_operator(
    owner, add_mev_boost_relays_factory, mev_boost_relay_test_config
):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when operator is longer than 255 characters"
    operator = "a" * (mev_boost_relay_test_config["max_string_length"] + 1)

    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([("uri", operator, True, "description")]))


def test_cannot_add_relay_with_over_max_uri_length(owner, add_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when uri is longer than 255 characters"
    uri = "a" * (mev_boost_relay_test_config["max_string_length"] + 1)

    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        add_mev_boost_relays_factory.createEVMScript(owner, create_calldata([(uri, "operator", True, "description")]))
