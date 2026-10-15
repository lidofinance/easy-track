// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {MEVBoostRelaysInputUtilsWrapper} from "contracts/test/MEVBoostRelaysInputUtilsWrapper.sol";

contract MEVBoostRelaysInputUtilsTest is Test {
    uint256 internal constant MAX_STRING_LENGTH = 1024;

    address internal owner = makeAddr("owner");

    MEVBoostRelaysInputUtilsWrapper internal wrapper;

    function setUp() public {
        vm.prank(owner);
        wrapper = new MEVBoostRelaysInputUtilsWrapper();
    }

    // python: test_validate_structs_passes_when_relay_found_as_expected
    function test_ValidateRelaysPassesWhenRelayFoundAsExpected() external view {
        IMEVBoostRelayAllowedList.Relay[] memory allowedRelays = _allowedRelays();

        wrapper.validateRelays(_single(allowedRelays[0]), allowedRelays, true);
    }

    // python: test_validate_structs_reverts_when_relay_not_found_expected
    function test_RevertWhen_ValidateRelaysExpectedRelayIsNotFound() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay =
            _relay("https://relay4.example.com", "Operator 4", true, "Fourth relay description");

        vm.expectRevert("RELAY_NOT_FOUND");
        wrapper.validateRelays(_single(newRelay), _allowedRelays(), true);
    }

    // python: test_validate_structs_passes_when_relay_absent_as_expected
    function test_ValidateRelaysPassesWhenRelayAbsentAsExpected() external view {
        IMEVBoostRelayAllowedList.Relay memory newRelay =
            _relay("https://relay4.example.com", "Operator 4", true, "Fourth relay description");

        wrapper.validateRelays(_single(newRelay), _allowedRelays(), false);
    }

    // python: test_validate_structs_reverts_when_relay_present_unexpected
    function test_RevertWhen_ValidateRelaysUnexpectedRelayIsPresent() external {
        IMEVBoostRelayAllowedList.Relay[] memory allowedRelays = _allowedRelays();

        vm.expectRevert("RELAY_URI_ALREADY_EXISTS");
        wrapper.validateRelays(_single(allowedRelays[0]), allowedRelays, false);
    }

    // python: test_validate_structs_reverts_on_empty_array
    function test_RevertWhen_ValidateRelaysArrayIsEmpty() external {
        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        wrapper.validateRelays(new IMEVBoostRelayAllowedList.Relay[](0), _allowedRelays(), true);
    }

    // python: test_validate_structs_reverts_on_empty_uri
    function test_RevertWhen_ValidateRelaysURIIsEmpty() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay =
            _relay("", "Operator 1", true, "Description 1");

        vm.expectRevert("EMPTY_RELAY_URI");
        wrapper.validateRelays(_single(newRelay), _allowedRelays(), true);
    }

    // python: test_validate_structs_reverts_on_uri_exceeding_max_length
    function test_RevertWhen_ValidateRelaysURIExceedsMaxLength() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay =
            _relay(_repeat("a", MAX_STRING_LENGTH + 1), "Operator 1", true, "Description 1");

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelays(_single(newRelay), _allowedRelays(), true);
    }

    // python: test_validate_structs_reverts_on_operator_exceeding_max_length
    function test_RevertWhen_ValidateRelaysOperatorExceedsMaxLength() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay = _relay(
            "https://example.com", _repeat("o", MAX_STRING_LENGTH + 1), true, "Description 1"
        );

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelays(_single(newRelay), _allowedRelays(), true);
    }

    // python: test_validate_structs_reverts_on_description_exceeding_max_length
    function test_RevertWhen_ValidateRelaysDescriptionExceedsMaxLength() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay =
            _relay("https://example.com", "Operator 1", true, _repeat("d", MAX_STRING_LENGTH + 1));

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelays(_single(newRelay), _allowedRelays(), true);
    }

    // python: test_validate_structs_reverts_on_duplicate_uris
    function test_RevertWhen_ValidateRelaysURIsAreDuplicated() external {
        IMEVBoostRelayAllowedList.Relay memory duplicateRelay =
            _relay("https://example.com", "Operator", true, "Description");

        // the duplicate check runs before the existence check
        vm.expectRevert("DUPLICATE_RELAY_URI");
        wrapper.validateRelays(_pair(duplicateRelay, duplicateRelay), _allowedRelays(), true);
    }

    // python: test_validate_uris_passes_when_relay_found_as_expected
    function test_ValidateRelayURIsPassesWhenRelayFoundAsExpected() external view {
        wrapper.validateRelayURIs(_single(_allowedURIs()[0]), _allowedRelays());
    }

    // python: test_validate_uris_reverts_when_relay_not_found_expected
    function test_RevertWhen_ValidateRelayURIsRelayIsNotFound() external {
        vm.expectRevert("RELAY_NOT_FOUND");
        wrapper.validateRelayURIs(_single("https://nonexistent.example.com"), _allowedRelays());
    }

    // python: test_validate_uris_reverts_on_empty_array
    function test_RevertWhen_ValidateRelayURIsArrayIsEmpty() external {
        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        wrapper.validateRelayURIs(new string[](0), _allowedRelays());
    }

    // python: test_validate_uris_reverts_on_empty_string
    function test_RevertWhen_ValidateRelayURIsURIIsEmpty() external {
        vm.expectRevert("EMPTY_RELAY_URI");
        wrapper.validateRelayURIs(_single(""), _allowedRelays());
    }

    // python: test_validate_uris_reverts_on_uri_exceeding_max_length
    function test_RevertWhen_ValidateRelayURIsURIExceedsMaxLength() external {
        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelayURIs(_single(_repeat("a", MAX_STRING_LENGTH + 1)), _allowedRelays());
    }

    // python: test_validate_uris_reverts_on_duplicate_entries
    function test_RevertWhen_ValidateRelayURIsEntriesAreDuplicated() external {
        vm.expectRevert("DUPLICATE_RELAY_URI");
        wrapper.validateRelayURIs(
            _pair("https://example.com", "https://example.com"), _allowedRelays()
        );
    }

    // python: test_decode_structs_returns_valid_relay_struct_array
    function test_DecodesRelayStructs() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = _allowedRelays();

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            wrapper.decodeCallDataWithRelayStructs(abi.encode(relays));

        _assertRelaysEq(decoded, relays);
    }

    // python: test_decode_structs_reverts_on_invalid_data
    function test_RevertWhen_DecodingRelayStructsFromInvalidData() external {
        // abi.decode of malformed input reverts with empty data
        vm.expectRevert(bytes(""));
        wrapper.decodeCallDataWithRelayStructs(hex"1234");
    }

    // python: test_decode_uris_returns_valid_relay_uri_array
    function test_DecodesRelayURIs() external view {
        string[] memory allowedURIs = _allowedURIs();

        string[] memory decoded = wrapper.decodeCallDataWithRelayURIs(abi.encode(allowedURIs));

        assertEq(decoded, allowedURIs, "uris");
    }

    // python: test_decode_uris_reverts_on_invalid_data
    function test_RevertWhen_DecodingRelayURIsFromInvalidData() external {
        // abi.decode of malformed input reverts with empty data
        vm.expectRevert(bytes(""));
        wrapper.decodeCallDataWithRelayURIs(hex"1234");
    }

    // python: mev_boost_relay_test_config["relays"]
    function _allowedRelays()
        private
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory relays)
    {
        relays = new IMEVBoostRelayAllowedList.Relay[](3);
        relays[0] =
            _relay("https://relay1.example.com", "Operator 1", true, "First relay description");
        relays[1] =
            _relay("https://relay2.example.com", "Operator 2", false, "Second relay description");
        relays[2] =
            _relay("https://relay3.example.com", "Operator 3", true, "Third relay description");
    }

    // python: allowed_uris
    function _allowedURIs() private pure returns (string[] memory uris) {
        IMEVBoostRelayAllowedList.Relay[] memory relays = _allowedRelays();
        uris = new string[](relays.length);
        for (uint256 i; i < relays.length; ++i) {
            uris[i] = relays[i].uri;
        }
    }

    function _relay(
        string memory uri,
        string memory operator,
        bool isMandatory,
        string memory description
    ) private pure returns (IMEVBoostRelayAllowedList.Relay memory) {
        return IMEVBoostRelayAllowedList.Relay({
                uri: uri, operator: operator, is_mandatory: isMandatory, description: description
            });
    }

    function _single(IMEVBoostRelayAllowedList.Relay memory relay)
        private
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory relays)
    {
        relays = new IMEVBoostRelayAllowedList.Relay[](1);
        relays[0] = relay;
    }

    function _pair(
        IMEVBoostRelayAllowedList.Relay memory first,
        IMEVBoostRelayAllowedList.Relay memory second
    ) private pure returns (IMEVBoostRelayAllowedList.Relay[] memory relays) {
        relays = new IMEVBoostRelayAllowedList.Relay[](2);
        relays[0] = first;
        relays[1] = second;
    }

    function _single(string memory uri) private pure returns (string[] memory uris) {
        uris = new string[](1);
        uris[0] = uri;
    }

    function _pair(string memory first, string memory second)
        private
        pure
        returns (string[] memory uris)
    {
        uris = new string[](2);
        uris[0] = first;
        uris[1] = second;
    }

    function _repeat(bytes1 char, uint256 count) private pure returns (string memory) {
        bytes memory result = new bytes(count);
        for (uint256 i; i < count; ++i) {
            result[i] = char;
        }

        return string(result);
    }

    function _assertRelaysEq(
        IMEVBoostRelayAllowedList.Relay[] memory actual,
        IMEVBoostRelayAllowedList.Relay[] memory expected
    ) private pure {
        assertEq(actual.length, expected.length, "relays.length");

        for (uint256 i; i < expected.length; ++i) {
            assertEq(actual[i].uri, expected[i].uri, "uri");
            assertEq(actual[i].operator, expected[i].operator, "operator");
            assertEq(actual[i].is_mandatory, expected[i].is_mandatory, "is_mandatory");
            assertEq(actual[i].description, expected[i].description, "description");
        }
    }
}
