// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Vm} from "forge-std/Vm.sol";
import {Strings} from "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/utils/Strings.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";

/// @notice The relay builders and encoders the MEV-Boost relay factory tests share
library MEVBoostRelays {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    uint256 internal constant MAX_NUM_RELAYS = 40;
    uint256 internal constant MAX_STRING_LENGTH = 1024;

    uint256 internal constant RELAYS_COUNT = 3;

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

    function relayURIs(uint256 count) internal pure returns (string[] memory uris) {
        uris = new string[](count);

        for (uint256 i; i < count; ++i) {
            uris[i] = relayAt(i).uri;
        }
    }

    /// @dev The relay the tests generate at index `i`
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

    /// @dev A string of `length` copies of `char`
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

    function removeRelayCallData(string memory uri) internal pure returns (bytes memory) {
        return abi.encodeWithSelector(IMEVBoostRelayAllowedList.remove_relay.selector, uri);
    }

    function addRelay(
        IMEVBoostRelayAllowedList list,
        address owner,
        IMEVBoostRelayAllowedList.Relay memory input
    ) internal {
        vm.prank(owner);
        list.add_relay(input.uri, input.operator, input.is_mandatory, input.description);
    }

    /// @dev `addRelay` for each of `inputs`
    function addRelays(
        IMEVBoostRelayAllowedList list,
        address owner,
        IMEVBoostRelayAllowedList.Relay[] memory inputs
    ) internal {
        for (uint256 i; i < inputs.length; ++i) {
            addRelay(list, owner, inputs[i]);
        }
    }

    /// @dev Field by field equality of two relay lists
    function assertRelaysEq(
        IMEVBoostRelayAllowedList.Relay[] memory actual,
        IMEVBoostRelayAllowedList.Relay[] memory expected
    ) internal pure {
        vm.assertEq(actual.length, expected.length, "relays.length");

        for (uint256 i; i < expected.length; ++i) {
            vm.assertEq(actual[i].uri, expected[i].uri, "uri");
            vm.assertEq(actual[i].operator, expected[i].operator, "operator");
            vm.assertEq(actual[i].is_mandatory, expected[i].is_mandatory, "is_mandatory");
            vm.assertEq(actual[i].description, expected[i].description, "description");
        }
    }
}
