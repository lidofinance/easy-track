// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {MEVBoostRelaysInputUtilsWrapper} from "contracts/test/MEVBoostRelaysInputUtilsWrapper.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {MEVBoostRelays} from "test/foundry/unit/helpers/MEVBoostRelays.sol";

contract MEVBoostRelaysInputUtilsTest is Test {
    address internal owner = makeAddr("owner");

    MEVBoostRelaysInputUtilsWrapper internal wrapper;

    function setUp() public {
        vm.prank(owner);
        wrapper = new MEVBoostRelaysInputUtilsWrapper();
    }

    function test_ValidatesRelaysWhenRelayFoundAsExpected() external view {
        IMEVBoostRelayAllowedList.Relay[] memory allowedRelays = _allowedRelays();

        wrapper.validateRelays(Arrays.list(allowedRelays[0]), allowedRelays, true);
    }

    function test_RevertWhen_ValidateRelaysExpectedRelayIsNotFound() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay = MEVBoostRelays.relay(
            "https://relay4.example.com", "Operator 4", true, "Fourth relay description"
        );

        vm.expectRevert("RELAY_NOT_FOUND");
        wrapper.validateRelays(Arrays.list(newRelay), _allowedRelays(), true);
    }

    function test_ValidatesRelaysWhenRelayAbsentAsExpected() external view {
        IMEVBoostRelayAllowedList.Relay memory newRelay = MEVBoostRelays.relay(
            "https://relay4.example.com", "Operator 4", true, "Fourth relay description"
        );

        wrapper.validateRelays(Arrays.list(newRelay), _allowedRelays(), false);
    }

    function test_RevertWhen_ValidateRelaysUnexpectedRelayIsPresent() external {
        IMEVBoostRelayAllowedList.Relay[] memory allowedRelays = _allowedRelays();

        vm.expectRevert("RELAY_URI_ALREADY_EXISTS");
        wrapper.validateRelays(Arrays.list(allowedRelays[0]), allowedRelays, false);
    }

    function test_RevertWhen_ValidateRelaysArrayIsEmpty() external {
        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        wrapper.validateRelays(new IMEVBoostRelayAllowedList.Relay[](0), _allowedRelays(), true);
    }

    function test_RevertWhen_ValidateRelaysURIIsEmpty() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay =
            MEVBoostRelays.relay("", "Operator 1", true, "Description 1");

        vm.expectRevert("EMPTY_RELAY_URI");
        wrapper.validateRelays(Arrays.list(newRelay), _allowedRelays(), true);
    }

    function test_RevertWhen_ValidateRelaysURIExceedsMaxLength() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay = MEVBoostRelays.relay(
            MEVBoostRelays.stringOf("a", MEVBoostRelays.MAX_STRING_LENGTH + 1),
            "Operator 1",
            true,
            "Description 1"
        );

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelays(Arrays.list(newRelay), _allowedRelays(), true);
    }

    function test_RevertWhen_ValidateRelaysOperatorExceedsMaxLength() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay = MEVBoostRelays.relay(
            "https://example.com",
            MEVBoostRelays.stringOf("o", MEVBoostRelays.MAX_STRING_LENGTH + 1),
            true,
            "Description 1"
        );

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelays(Arrays.list(newRelay), _allowedRelays(), true);
    }

    function test_RevertWhen_ValidateRelaysDescriptionExceedsMaxLength() external {
        IMEVBoostRelayAllowedList.Relay memory newRelay = MEVBoostRelays.relay(
            "https://example.com",
            "Operator 1",
            true,
            MEVBoostRelays.stringOf("d", MEVBoostRelays.MAX_STRING_LENGTH + 1)
        );

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelays(Arrays.list(newRelay), _allowedRelays(), true);
    }

    function test_RevertWhen_ValidateRelaysURIsAreDuplicated() external {
        IMEVBoostRelayAllowedList.Relay memory duplicateRelay =
            MEVBoostRelays.relay("https://example.com", "Operator", true, "Description");

        // the duplicate check runs before the existence check
        vm.expectRevert("DUPLICATE_RELAY_URI");
        wrapper.validateRelays(Arrays.list(duplicateRelay, duplicateRelay), _allowedRelays(), true);
    }

    function test_ValidatesRelayURIsWhenRelayFoundAsExpected() external view {
        wrapper.validateRelayURIs(Arrays.list(_allowedURIs()[0]), _allowedRelays());
    }

    function test_RevertWhen_ValidateRelayURIsRelayIsNotFound() external {
        vm.expectRevert("RELAY_NOT_FOUND");
        wrapper.validateRelayURIs(
            Arrays.list(string("https://nonexistent.example.com")), _allowedRelays()
        );
    }

    function test_RevertWhen_ValidateRelayURIsArrayIsEmpty() external {
        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        wrapper.validateRelayURIs(new string[](0), _allowedRelays());
    }

    function test_RevertWhen_ValidateRelayURIsURIIsEmpty() external {
        vm.expectRevert("EMPTY_RELAY_URI");
        wrapper.validateRelayURIs(Arrays.list(string("")), _allowedRelays());
    }

    function test_RevertWhen_ValidateRelayURIsURIExceedsMaxLength() external {
        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        wrapper.validateRelayURIs(
            Arrays.list(MEVBoostRelays.stringOf("a", MEVBoostRelays.MAX_STRING_LENGTH + 1)),
            _allowedRelays()
        );
    }

    function test_RevertWhen_ValidateRelayURIsEntriesAreDuplicated() external {
        vm.expectRevert("DUPLICATE_RELAY_URI");
        wrapper.validateRelayURIs(
            Arrays.list(string("https://example.com"), string("https://example.com")),
            _allowedRelays()
        );
    }

    function test_DecodesRelayStructs() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = _allowedRelays();

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            wrapper.decodeCallDataWithRelayStructs(abi.encode(relays));

        MEVBoostRelays.assertRelaysEq(decoded, relays);
    }

    function test_RevertWhen_DecodingRelayStructsFromInvalidData() external {
        // abi.decode of malformed input reverts with empty data
        vm.expectRevert(bytes(""));
        wrapper.decodeCallDataWithRelayStructs(hex"1234");
    }

    function test_DecodesRelayURIs() external view {
        string[] memory allowedURIs = _allowedURIs();

        string[] memory decoded = wrapper.decodeCallDataWithRelayURIs(abi.encode(allowedURIs));

        assertEq(decoded, allowedURIs, "uris");
    }

    function test_RevertWhen_DecodingRelayURIsFromInvalidData() external {
        // abi.decode of malformed input reverts with empty data
        vm.expectRevert(bytes(""));
        wrapper.decodeCallDataWithRelayURIs(hex"1234");
    }

    function _allowedRelays() private pure returns (IMEVBoostRelayAllowedList.Relay[] memory) {
        return MEVBoostRelays.relays(MEVBoostRelays.RELAYS_COUNT);
    }

    function _allowedURIs() private pure returns (string[] memory) {
        return MEVBoostRelays.relayURIs(MEVBoostRelays.RELAYS_COUNT);
    }
}
