// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Strings} from "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/utils/Strings.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";

/// @notice python: mev_boost_relay_test_config of `tests/conftest.py`, with the relay builders and
/// encoders the MEV-Boost relay factory tests share
library MEVBoostRelays {
    uint256 internal constant MAX_NUM_RELAYS = 40;
    uint256 internal constant MAX_STRING_LENGTH = 1024;

    /// @dev python: len(mev_boost_relay_test_config["relays"])
    uint256 internal constant RELAYS_COUNT = 3;

    /// @dev python: mev_boost_relay_test_config["relays"][index]
    function relayAt(uint256 index) internal pure returns (IMEVBoostRelayAllowedList.Relay memory) {
        IMEVBoostRelayAllowedList.Relay[] memory all =
            new IMEVBoostRelayAllowedList.Relay[](RELAYS_COUNT);

        all[0] = IMEVBoostRelayAllowedList.Relay({
            uri: "https://relay1.example.com",
            operator: "Operator 1",
            is_mandatory: true,
            description: "First relay description"
        });

        all[1] = IMEVBoostRelayAllowedList.Relay({
            uri: "https://relay2.example.com",
            operator: "Operator 2",
            is_mandatory: false,
            description: "Second relay description"
        });

        all[2] = IMEVBoostRelayAllowedList.Relay({
            uri: "https://relay3.example.com",
            operator: "Operator 3",
            is_mandatory: true,
            description: "Third relay description"
        });

        return all[index];
    }

    /// @dev python: mev_boost_relay_test_config["relays"][:count]
    function relays(uint256 count)
        internal
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory result)
    {
        result = new IMEVBoostRelayAllowedList.Relay[](count);

        for (uint256 i; i < count; ++i) {
            result[i] = relayAt(i);
        }
    }

    /// @dev python: get_relay_fixture_uri(i) for the first `count` fixture relays
    function relayURIs(uint256 count) internal pure returns (string[] memory uris) {
        uris = new string[](count);

        for (uint256 i; i < count; ++i) {
            uris[i] = relayAt(i).uri;
        }
    }

    /// @dev python: ("uri{i}", "operator{i}", True, "description{i}"), the relay the tests generate
    /// at index `i`
    function generatedRelay(uint256 i)
        internal
        pure
        returns (IMEVBoostRelayAllowedList.Relay memory)
    {
        string memory suffix = Strings.toString(i);

        return relay(
            string(abi.encodePacked("uri", suffix)),
            string(abi.encodePacked("operator", suffix)),
            true,
            string(abi.encodePacked("description", suffix))
        );
    }

    /// @dev The generated relays at indices `0 .. count - 1`
    function generatedRelays(uint256 count)
        internal
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory result)
    {
        result = new IMEVBoostRelayAllowedList.Relay[](count);

        for (uint256 i; i < count; ++i) {
            result[i] = generatedRelay(i);
        }
    }

    /// @dev python: "https://relay{i}.example.com" for i in 0 .. count - 1
    function exampleURIs(uint256 count) internal pure returns (string[] memory uris) {
        uris = new string[](count);

        for (uint256 relayIndex; relayIndex < count; ++relayIndex) {
            uris[relayIndex] = string(
                abi.encodePacked("https://relay", Strings.toString(relayIndex), ".example.com")
            );
        }
    }

    /// @dev The `uri` of every relay in `list`
    function urisOf(IMEVBoostRelayAllowedList.Relay[] memory list)
        internal
        pure
        returns (string[] memory uris)
    {
        uris = new string[](list.length);

        for (uint256 i; i < list.length; ++i) {
            uris[i] = list[i].uri;
        }
    }

    /// @dev python: "a" * length and the like. `length` copies of `char`
    function stringOf(bytes1 char, uint256 length) internal pure returns (string memory) {
        bytes memory result = new bytes(length);

        for (uint256 i; i < length; ++i) {
            result[i] = char;
        }

        return string(result);
    }

    /// @dev A relay struct from its four fields
    function relay(
        string memory uri,
        string memory operator,
        bool isMandatory,
        string memory description
    ) internal pure returns (IMEVBoostRelayAllowedList.Relay memory) {
        return IMEVBoostRelayAllowedList.Relay({
                uri: uri, operator: operator, is_mandatory: isMandatory, description: description
            });
    }

    /// @dev python: mev_boost_relay_allowed_list_stub.add_relay.encode_input(*relay)
    function addRelayCallData(IMEVBoostRelayAllowedList.Relay memory input)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            IMEVBoostRelayAllowedList.add_relay.selector,
            input.uri,
            input.operator,
            input.is_mandatory,
            input.description
        );
    }

    /// @dev python: mev_boost_relay_allowed_list_stub.remove_relay.encode_input(uri)
    function removeRelayCallData(string memory uri) internal pure returns (bytes memory) {
        return abi.encodeWithSelector(IMEVBoostRelayAllowedList.remove_relay.selector, uri);
    }
}
