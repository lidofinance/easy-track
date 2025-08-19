import pytest
from eth_abi import encode
from brownie import reverts, EditMEVBoostRelays

from utils.evm_script import encode_call_script


def create_calldata(data):
    return "0x" + encode(["(string,string,bool,string)[]"], [data]).hex()


@pytest.fixture(scope="module")
def edit_mev_boost_relays_factory(owner, mev_boost_relay_allowed_list_stub):
    return EditMEVBoostRelays.deploy(owner, mev_boost_relay_allowed_list_stub, {"from": owner})


def test_deploy(mev_boost_relay_allowed_list_stub, owner, edit_mev_boost_relays_factory):
    "Must deploy contract with correct data"
    assert edit_mev_boost_relays_factory.trustedCaller() == owner
    assert edit_mev_boost_relays_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list_stub


def test_decode_evm_script_call_data_single_relay(edit_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly"
    input_params = [mev_boost_relay_test_config["relays"][0]]
    calldata = create_calldata(input_params)

    assert edit_mev_boost_relays_factory.decodeEVMScriptCallData(calldata) == (
        mev_boost_relay_test_config["relays"][0],
    )


def test_decode_evm_script_call_data_multiple_relays(edit_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(mev_boost_relay_test_config["relays"])
    assert edit_mev_boost_relays_factory.decodeEVMScriptCallData(calldata) == mev_boost_relay_test_config["relays"]


def test_edit_single_relay(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must create correct EVMScript to edit single relay"
    input_params = [mev_boost_relay_test_config["relays"][0]]

    mev_boost_relay_allowed_list_stub.add_relay(*input_params[0], {"from": owner})

    calldata = create_calldata(input_params)
    direct_allow_list_calldata = [
        (
            mev_boost_relay_allowed_list_stub.address,
            mev_boost_relay_allowed_list_stub.remove_relay.encode_input(
                mev_boost_relay_test_config["relays"][0][0],
            ),
        ),
        (
            mev_boost_relay_allowed_list_stub.address,
            mev_boost_relay_allowed_list_stub.add_relay.encode_input(
                *input_params[0],
            ),
        ),
    ]

    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)
    expected_evm_script = encode_call_script(direct_allow_list_calldata)

    assert evm_script == expected_evm_script


def test_edit_multiple_relays(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must create correct EVMScript to edit multiple relays"
    calldata = create_calldata(mev_boost_relay_test_config["relays"])
    direct_allow_list_calldata = []

    for relay in mev_boost_relay_test_config["relays"]:
        mev_boost_relay_allowed_list_stub.add_relay(*relay, {"from": owner})

        direct_allow_list_calldata += [
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.remove_relay.encode_input(relay[0]),
            ),
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.add_relay.encode_input(
                    *relay,
                ),
            ),
        ]

    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)
    expected_evm_script = encode_call_script(direct_allow_list_calldata)

    assert evm_script == expected_evm_script


def test_edit_max_num_relays(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must create correct EVMScript to edit maximum number of relays at once"

    inputs = []
    direct_allow_list_calldata = []

    for i in range(mev_boost_relay_test_config["max_num_relays"]):
        relay = (f"uri{i}", f"operator{i}", True, f"description{i}")

        mev_boost_relay_allowed_list_stub.add_relay(*relay, {"from": owner})

        inputs.append(relay)
        direct_allow_list_calldata += [
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.remove_relay.encode_input(relay[0]),
            ),
            (
                mev_boost_relay_allowed_list_stub.address,
                mev_boost_relay_allowed_list_stub.add_relay.encode_input(
                    *relay,
                ),
            ),
        ]

    calldata = create_calldata(inputs)
    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(direct_allow_list_calldata)
    assert evm_script == expected_evm_script


def test_can_edit_relay_and_set_description_to_empty(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must create correct EVMScript to edit relay with empty description"
    input_params = [
        (
            mev_boost_relay_test_config["relays"][0][0],
            mev_boost_relay_test_config["relays"][0][1],
            mev_boost_relay_test_config["relays"][0][2],
            "",
        )
    ]
    mev_boost_relay_allowed_list_stub.add_relay(*mev_boost_relay_test_config["relays"][0], {"from": owner})

    calldata = create_calldata(input_params)
    direct_allow_list_calldata = [
        (
            mev_boost_relay_allowed_list_stub.address,
            mev_boost_relay_allowed_list_stub.remove_relay.encode_input(
                mev_boost_relay_test_config["relays"][0][0],
            ),
        ),
        (
            mev_boost_relay_allowed_list_stub.address,
            mev_boost_relay_allowed_list_stub.add_relay.encode_input(
                *input_params[0],
            ),
        ),
    ]

    evm_script = edit_mev_boost_relays_factory.createEVMScript(owner, calldata)
    expected_evm_script = encode_call_script(direct_allow_list_calldata)

    assert evm_script == expected_evm_script


def test_can_edit_relay_and_set_operator_to_empty(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must create correct EVMScript to edit relay with empty operator"
    input_params = [
        (
            mev_boost_relay_test_config["relays"][0][0],
            "",
            mev_boost_relay_test_config["relays"][0][2],
            mev_boost_relay_test_config["relays"][0][3],
        )
    ]

    mev_boost_relay_allowed_list_stub.add_relay(*mev_boost_relay_test_config["relays"][0], {"from": owner})

    calldata = create_calldata(input_params)
    direct_allow_list_calldata = [
        (
            mev_boost_relay_allowed_list_stub.address,
            mev_boost_relay_allowed_list_stub.remove_relay.encode_input(
                mev_boost_relay_test_config["relays"][0][0],
            ),
        ),
        (
            mev_boost_relay_allowed_list_stub.address,
            mev_boost_relay_allowed_list_stub.add_relay.encode_input(
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


def test_cannot_edit_relay_with_empty_calldata(owner, edit_mev_boost_relays_factory):
    "Must revert with message 'EMPTY_RELAYS_ARRAY' when calldata is empty"
    with reverts("EMPTY_RELAYS_ARRAY"):
        edit_mev_boost_relays_factory.createEVMScript(owner, create_calldata([]))


def test_cannot_edit_relay_with_empty_uri(owner, edit_mev_boost_relays_factory):
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


def test_cannot_edit_relay_with_duplicate_uri(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must revert with message 'DUPLICATE_RELAY_URI' when uri is duplicated"
    relays = [
        (mev_boost_relay_test_config["relays"][0][0], "operator 1", True, "description 1"),
        (mev_boost_relay_test_config["relays"][0][0], "operator 2", False, "description 2"),
    ]

    mev_boost_relay_allowed_list_stub.add_relay(*relays[0], {"from": owner})

    with reverts("DUPLICATE_RELAY_URI"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(relays),
        )


def test_cannot_edit_relay_not_in_allow_list(owner, edit_mev_boost_relays_factory, mev_boost_relay_test_config):
    "Must revert with message 'RELAY_NOT_FOUND' when relay is not in the allow list"
    with reverts("RELAY_NOT_FOUND"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata([mev_boost_relay_test_config["relays"][0]]),
        )


def test_cannot_edit_relay_not_in_allow_list_with_multiple_relays(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must revert with message 'RELAY_NOT_FOUND' when relay is not in the allow list"
    # Add one relay to the allow list
    mev_boost_relay_allowed_list_stub.add_relay(*mev_boost_relay_test_config["relays"][0], {"from": owner})

    # Try to edit two relays, one of them is not in the allow list
    with reverts("RELAY_NOT_FOUND"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(mev_boost_relay_test_config["relays"][:2]),
        )


def test_cannot_edit_multiple_relays_when_last_not_in_allow_list(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_allowed_list_stub, mev_boost_relay_test_config
):
    "Must revert with message 'RELAY_NOT_FOUND' with multiple relays when the last one is not in the allow list"
    # Add all relays except the last one to the allow list, then try to edit all of them
    for relay in mev_boost_relay_test_config["relays"][:-1]:
        mev_boost_relay_allowed_list_stub.add_relay(*relay, {"from": owner})

    assert mev_boost_relay_allowed_list_stub.get_relays_amount() == len(mev_boost_relay_test_config["relays"]) - 1

    with reverts("RELAY_NOT_FOUND"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(mev_boost_relay_test_config["relays"]),
        )


def test_cannot_edit_relay_with_uri_over_max_string_length(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_test_config
):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when uri is over max string length"
    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    (
                        "u" * (mev_boost_relay_test_config["max_string_length"] + 1),
                        f"operator{i}",
                        True,
                        f"description{i}",
                    )
                    for i in range(mev_boost_relay_test_config["max_num_relays"])
                ]
            ),
        )


def test_cannot_edit_relay_with_operator_over_max_string_length(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_test_config
):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when operator is over max string length"
    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    (f"uri{i}", "o" * (mev_boost_relay_test_config["max_string_length"] + 1), True, f"description{i}")
                    for i in range(mev_boost_relay_test_config["max_num_relays"])
                ]
            ),
        )


def test_cannot_edit_relay_with_description_over_max_string_length(
    owner, edit_mev_boost_relays_factory, mev_boost_relay_test_config
):
    "Must revert with message 'MAX_STRING_LENGTH_EXCEEDED' when description is over max string length"
    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        edit_mev_boost_relays_factory.createEVMScript(
            owner,
            create_calldata(
                [
                    (f"uri{i}", f"operator{i}", True, "d" * (mev_boost_relay_test_config["max_string_length"] + 1))
                    for i in range(mev_boost_relay_test_config["max_num_relays"])
                ]
            ),
        )
