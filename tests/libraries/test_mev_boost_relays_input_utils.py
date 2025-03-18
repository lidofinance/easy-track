import pytest

from eth_abi import encode
from brownie import reverts

## Constants

RELAY_STRUCTS_PARAMS = "tuple[],tuple[],bool"
RELAY_URIS_PARAMS = "string[],tuple[],bool"


def create_struct_calldata(data):
    return "0x" + encode(["(string,string,bool,string)[]"], [data]).hex()


def create_uri_calldata(data):
    return "0x" + encode(["string[]"], [data]).hex()


@pytest.fixture(scope="module")
def allowed_uris(mev_boost_relay_test_config):
    return [relay[0] for relay in mev_boost_relay_test_config["relays"]]


# Relay Struct Array Validation Tests
def test_validate_structs_passes_when_relay_found_as_expected(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must pass when a relay struct is found by its URI in the allowed list and it is expected to be present"
    allowed_relays = mev_boost_relay_test_config["relays"]
    relay_input = [allowed_relays[0]]

    mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
        relay_input, allowed_relays, True, {"from": stranger}
    )


def test_validate_structs_reverts_when_relay_not_found_expected(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when a relay struct is not found in the allowed list but is expected to be present"
    allowed_relays = mev_boost_relay_test_config["relays"]
    new_relay = ("https://relay4.example.com", "Operator 4", True, "Fourth relay description")
    relay_input = [new_relay]

    with reverts("RELAY_NOT_FOUND"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            relay_input, allowed_relays, True, {"from": stranger}
        )


def test_validate_structs_passes_when_relay_absent_as_expected(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must pass when a relay struct is absent from the allowed list and it is expected not to be present"
    allowed_relays = mev_boost_relay_test_config["relays"]
    new_relay = ("https://relay4.example.com", "Operator 4", True, "Fourth relay description")

    mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
        [new_relay], allowed_relays, False, {"from": stranger}
    )


def test_validate_structs_reverts_when_relay_present_unexpected(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when a relay struct is present in the allowed list but is expected not to be present"
    allowed_relays = mev_boost_relay_test_config["relays"]
    relay_input = [allowed_relays[0]]

    with reverts("RELAY_URI_ALREADY_EXISTS"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            relay_input, allowed_relays, False, {"from": stranger}
        )


def test_validate_structs_reverts_on_empty_array(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when the relay struct array is empty"
    allowed_relays = mev_boost_relay_test_config["relays"]

    with reverts("EMPTY_RELAYS_ARRAY"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            [], allowed_relays, True, {"from": stranger}
        )


def test_validate_structs_reverts_on_empty_uri(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when a relay struct contains an empty URI"
    allowed_relays = mev_boost_relay_test_config["relays"]
    new_relay = ("", "Operator 1", True, "Description 1")

    with reverts("EMPTY_RELAY_URI"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            [new_relay], allowed_relays, True, {"from": stranger}
        )


def test_validate_structs_reverts_on_uri_exceeding_max_length(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when a relay struct's URI exceeds the maximum allowed length"
    allowed_relays = mev_boost_relay_test_config["relays"]
    max_length = mev_boost_relay_test_config["max_string_length"]
    long_uri = "a" * (max_length + 1)
    new_relay = (long_uri, "Operator 1", True, "Description 1")

    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            [new_relay], allowed_relays, True, {"from": stranger}
        )


def test_validate_structs_reverts_on_operator_exceeding_max_length(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when a relay struct's operator string exceeds the maximum allowed length"
    allowed_relays = mev_boost_relay_test_config["relays"]
    max_length = mev_boost_relay_test_config["max_string_length"]
    long_operator = "o" * (max_length + 1)
    new_relay = ("https://example.com", long_operator, True, "Description 1")

    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            [new_relay], allowed_relays, True, {"from": stranger}
        )


def test_validate_structs_reverts_on_description_exceeding_max_length(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when a relay struct's description string exceeds the maximum allowed length"
    allowed_relays = mev_boost_relay_test_config["relays"]
    max_length = mev_boost_relay_test_config["max_string_length"]
    long_description = "d" * (max_length + 1)
    new_relay = ("https://example.com", "Operator 1", True, long_description)

    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            [new_relay], allowed_relays, True, {"from": stranger}
        )


def test_validate_structs_reverts_on_duplicate_uris(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when there are duplicate URIs within the relay struct array"
    allowed_relays = mev_boost_relay_test_config["relays"]
    duplicate_relay = ("https://example.com", "Operator", True, "Description")
    relay_input = [duplicate_relay, duplicate_relay]

    with reverts("DUPLICATE_RELAY_URI"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_STRUCTS_PARAMS](
            relay_input, allowed_relays, True, {"from": stranger}
        )


# Relay URI String Array Validation Tests
def test_validate_uris_passes_when_relay_found_as_expected(
    mev_boost_relay_input_utils_wrapper, allowed_uris, stranger, mev_boost_relay_test_config
):
    "Must pass when a relay URI is found in the allowed list and it is expected to be present"
    relay_input = [allowed_uris[0]]

    mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
        relay_input, mev_boost_relay_test_config["relays"], True, {"from": stranger}
    )


def test_validate_uris_reverts_when_relay_not_found_expected(
    mev_boost_relay_input_utils_wrapper, allowed_uris, stranger, mev_boost_relay_test_config
):
    "Must revert when a relay URI is not found in the allowed list but is expected to be present"
    relay_input = ["https://nonexistent.example.com"]

    with reverts("RELAY_NOT_FOUND"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
            relay_input, mev_boost_relay_test_config["relays"], True, {"from": stranger}
        )


def test_validate_uris_passes_when_relay_absent_as_expected(
    mev_boost_relay_input_utils_wrapper, allowed_uris, stranger, mev_boost_relay_test_config
):
    "Must pass when a relay URI is absent from the allowed list and it is expected not to be present"
    relay_input = ["https://relay4.example.com"]

    mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
        relay_input, mev_boost_relay_test_config["relays"], False, {"from": stranger}
    )


def test_validate_uris_reverts_when_relay_present_unexpected(
    mev_boost_relay_input_utils_wrapper, allowed_uris, stranger, mev_boost_relay_test_config
):
    "Must revert when a relay URI is present in the allowed list but is expected not to be present"
    relay_input = [allowed_uris[0]]

    with reverts("RELAY_URI_ALREADY_EXISTS"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
            relay_input, mev_boost_relay_test_config["relays"], False, {"from": stranger}
        )


def test_validate_uris_reverts_on_empty_array(
    mev_boost_relay_input_utils_wrapper, stranger, mev_boost_relay_test_config
):
    "Must revert when the relay URI array is empty"

    with reverts("EMPTY_RELAYS_ARRAY"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
            [], mev_boost_relay_test_config["relays"], True, {"from": stranger}
        )


def test_validate_uris_reverts_on_empty_string(
    mev_boost_relay_input_utils_wrapper, stranger, mev_boost_relay_test_config
):
    "Must revert when a relay URI string is empty"
    relay_input = [""]

    with reverts("EMPTY_RELAY_URI"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
            relay_input, mev_boost_relay_test_config["relays"], True, {"from": stranger}
        )


def test_validate_uris_reverts_on_uri_exceeding_max_length(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config, stranger
):
    "Must revert when a relay URI exceeds the maximum allowed length"
    max_length = mev_boost_relay_test_config["max_string_length"]
    long_uri = "a" * (max_length + 1)
    relay_input = [long_uri]

    with reverts("MAX_STRING_LENGTH_EXCEEDED"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
            relay_input, mev_boost_relay_test_config["relays"], True, {"from": stranger}
        )


def test_validate_uris_reverts_on_duplicate_entries(
    mev_boost_relay_input_utils_wrapper, stranger, mev_boost_relay_test_config
):
    "Must revert when there are duplicate entries in the relay URI array"
    duplicate_uri = "https://example.com"
    relay_input = [duplicate_uri, duplicate_uri]

    with reverts("DUPLICATE_RELAY_URI"):
        mev_boost_relay_input_utils_wrapper.validateRelays[RELAY_URIS_PARAMS](
            relay_input, mev_boost_relay_test_config["relays"], True, {"from": stranger}
        )


# Decoding Function Tests
def test_decode_structs_returns_valid_relay_struct_array(
    mev_boost_relay_input_utils_wrapper, mev_boost_relay_test_config
):
    "Must return a valid array of relay structs when provided with correctly encoded call data"
    relays = mev_boost_relay_test_config["relays"]
    calldata = create_struct_calldata(relays)

    result = mev_boost_relay_input_utils_wrapper.decodeCallDataWithRelayStructs(calldata)

    assert result == relays, "Decoded relay structs do not match the expected input"


def test_decode_structs_reverts_on_invalid_data(mev_boost_relay_input_utils_wrapper):
    "Must revert when decoding relay struct call data that is not a valid array of relay structs"
    invalid_calldata = "0x1234"

    with reverts():
        mev_boost_relay_input_utils_wrapper.decodeCallDataWithRelayStructs(invalid_calldata)


def test_decode_uris_returns_valid_relay_uri_array(mev_boost_relay_input_utils_wrapper, allowed_uris):
    "Must return a valid array of relay URIs when provided with correctly encoded call data"
    calldata = create_uri_calldata(allowed_uris)

    result = mev_boost_relay_input_utils_wrapper.decodeCallDataWithRelayURIs(calldata)

    assert result == allowed_uris, "Decoded relay URIs do not match the expected input"


def test_decode_uris_reverts_on_invalid_data(mev_boost_relay_input_utils_wrapper):
    "Must revert when decoding relay URI call data that is not a valid array of relay URIs"
    invalid_calldata = "0x1234"

    with reverts():
        mev_boost_relay_input_utils_wrapper.decodeCallDataWithRelayURIs(invalid_calldata)
