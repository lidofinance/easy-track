import pytest
from eth_abi import encode
from brownie import reverts, RemoveMEVBoostRelays, web3

from utils.evm_script import encode_call_script

RELAY_URIS = [
    "https://relay1.example.com",
    "https://relay2.example.com",
]

OPERATORS = [
    "Operator 1",
    "Operator 2",
]

IS_MANDATORY = [
    True,
    False,
]

DESCRIPTIONS = [
    "First relay description",
    "Second relay description",
]

def create_calldata(data):
    return (
        "0x"
        + encode(
            ["string[]"],
            [data],
        ).hex()
    )

@pytest.fixture(scope="module")
def remove_mev_boost_relays_factory(owner, mev_boost_relay_allowed_list):
    return RemoveMEVBoostRelays.deploy(owner, mev_boost_relay_allowed_list, {"from": owner})

def test_deploy(mev_boost_relay_allowed_list, owner, remove_mev_boost_relays_factory):
    "Must deploy contract with correct data"
    assert remove_mev_boost_relays_factory.trustedCaller() == owner
    assert remove_mev_boost_relays_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list

def test_create_evm_script_called_by_stranger(stranger, remove_mev_boost_relays_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        remove_mev_boost_relays_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)

def test_empty_calldata(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'EMPTY_CALLDATA' when no URIs provided"
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = create_calldata([])
        remove_mev_boost_relays_factory.createEVMScript(owner, EMPTY_CALLDATA)

def test_empty_relay_uri(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'EMPTY_RELAY_URI' when uri is empty"
    with reverts("EMPTY_RELAY_URI"):
        CALLDATA = create_calldata([""])
        remove_mev_boost_relays_factory.createEVMScript(owner, CALLDATA)

def test_relays_count_mismatch(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'RELAYS_COUNT_MISMATCH' when trying to remove more relays than exist"

    current_relay_count = mev_boost_relay_allowed_list.get_relays_amount()

    # Create array of URIs that is larger than the current relay count
    uris_to_remove = []
    for i in range(current_relay_count + 1):  # One more than exists
        uris_to_remove.append(f"https://relay{i}.example.com")

    with reverts("RELAYS_COUNT_MISMATCH"):
        CALLDATA = create_calldata(uris_to_remove)
        remove_mev_boost_relays_factory.createEVMScript(owner, CALLDATA)

def test_no_relay_with_given_uri(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must revert with message 'NO_RELAY_WITH_GIVEN_URI' when trying to remove non-existent relay"
    # Try to remove a relay that doesn't exist
    with reverts("NO_RELAY_WITH_GIVEN_URI"):
        CALLDATA = create_calldata([RELAY_URIS[0]])
        remove_mev_boost_relays_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, remove_mev_boost_relays_factory, mev_boost_relay_allowed_list):
    "Must create correct EVMScript if all requirements are met"

    # First add relays that we'll then remove
    for i in range(2):
        mev_boost_relay_allowed_list.add_relay(
            RELAY_URIS[i],
            OPERATORS[i],
            IS_MANDATORY[i],
            DESCRIPTIONS[i],
            {"from": owner}
        )

    # Create script to remove both relays
    CALLDATA = create_calldata([RELAY_URIS[0], RELAY_URIS[1]])
    evm_script = remove_mev_boost_relays_factory.createEVMScript(owner, CALLDATA)

    # Create expected script
    scripts = []
    for uri in [RELAY_URIS[0], RELAY_URIS[1]]:
        scripts.append(
            (
                mev_boost_relay_allowed_list.address,
                mev_boost_relay_allowed_list.remove_relay.encode_input(uri)
            )
        )

    expected_evm_script = encode_call_script(scripts)
    assert evm_script == expected_evm_script

def test_decode_evm_script_call_data(remove_mev_boost_relays_factory):
    "Must decode EVMScript call data correctly"
    input_uris = [RELAY_URIS[0], RELAY_URIS[1]]
    EVM_SCRIPT_CALLDATA = create_calldata(input_uris)

    decoded_uris = remove_mev_boost_relays_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_uris == input_uris
