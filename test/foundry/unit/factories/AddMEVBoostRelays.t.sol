// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AddMEVBoostRelays} from "contracts/EVMScriptFactories/AddMEVBoostRelays.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {MEVBoostRelayAllowedListStub} from "contracts/test/MEVBoostRelayAllowedListStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {MEVBoostRelays} from "test/foundry/unit/helpers/MEVBoostRelays.sol";

contract AddMEVBoostRelaysTest is Test {
    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal agent = makeAddr("agent");

    MEVBoostRelayAllowedListStub internal mevBoostRelayAllowedListStub;
    AddMEVBoostRelays internal addMEVBoostRelays;

    function setUp() public {
        mevBoostRelayAllowedListStub = new MEVBoostRelayAllowedListStub(agent, owner);

        vm.prank(owner);
        addMEVBoostRelays = new AddMEVBoostRelays(owner, address(mevBoostRelayAllowedListStub));

        vm.label(address(mevBoostRelayAllowedListStub), "mevBoostRelayAllowedListStub");
        vm.label(address(addMEVBoostRelays), "addMEVBoostRelays");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(addMEVBoostRelays.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(addMEVBoostRelays.mevBoostRelayAllowedList()),
            address(mevBoostRelayAllowedListStub),
            "mevBoostRelayAllowedList"
        );
    }

    // python: test_decode_evm_script_call_data_with_single_relay
    function test_DecodesEVMScriptCallDataWithSingleRelay() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            addMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        _assertRelaysEq(decoded, relays);
    }

    // python: test_decode_evm_script_call_data_multiple_relays
    function test_DecodesEVMScriptCallDataWithMultipleRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(2);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            addMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        _assertRelaysEq(decoded, relays);
    }

    // python: test_decode_evm_script_call_data_with_max_relays
    function test_DecodesEVMScriptCallDataWithMaxRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            addMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        _assertRelaysEq(decoded, relays);
    }

    // python: test_decode_evm_script_call_data_reverts_with_empty_calldata
    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        addMEVBoostRelays.decodeEVMScriptCallData("");
    }

    // python: test_create_evm_script_with_one_relay
    function test_CreatesEVMScriptWithOneRelay() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    // python: test_create_evm_script_with_multiple_relays
    function test_CreatesEVMScriptWithMultipleRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.relays(MEVBoostRelays.RELAYS_COUNT);

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    // python: test_add_max_num_relays
    function test_AddsMaxNumRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    // python: test_cannot_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        addMEVBoostRelays.createEVMScript(stranger, "");
    }

    // python: test_cannot_add_relay_with_empty_calldata
    function test_RevertWhen_RelaysAreEmpty() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = new IMEVBoostRelayAllowedList.Relay[](0);

        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_add_relay_with_empty_relay_uri
    function test_RevertWhen_RelayUriIsEmpty() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay("", "operator", true, "description"));

        vm.expectRevert("EMPTY_RELAY_URI");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_add_more_relays_than_allowed
    function test_RevertWhen_AddingMoreRelaysThanAllowed() external {
        _givenRelaysAdded(MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS));

        vm.expectRevert("MAX_NUM_RELAYS_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(MEVBoostRelays.relays(1)));
    }

    // python: test_cannot_batch_add_more_relays_than_allowed
    function test_RevertWhen_BatchAddingMoreRelaysThanAllowed() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS + 1);

        vm.expectRevert("MAX_NUM_RELAYS_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_add_relay_uri_already_exists
    function test_RevertWhen_RelayUriAlreadyExists() external {
        IMEVBoostRelayAllowedList.Relay memory relay = MEVBoostRelays.relayAt(0);
        _givenRelayAdded(relay);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), 1, "get_relays_amount");
        assertEq(mevBoostRelayAllowedListStub.get_relay_by_uri(relay.uri).uri, relay.uri, "uri");

        vm.expectRevert("RELAY_URI_ALREADY_EXISTS");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(_relays(relay)));
    }

    // python: test_cannot_add_relays_with_duplicate_uri
    function test_RevertWhen_RelaysHaveDuplicateUri() external {
        IMEVBoostRelayAllowedList.Relay memory duplicate = MEVBoostRelays.relayAt(1);
        duplicate.uri = MEVBoostRelays.relayAt(0).uri;

        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relayAt(0), duplicate);

        vm.expectRevert("DUPLICATE_RELAY_URI");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_can_add_relay_with_max_uri_length
    function test_AddsRelayWithMaxUriLength() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay(_stringOfMaxLength(), "operator", true, "description"));

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    // python: test_can_add_relay_with_max_string_length_description
    function test_AddsRelayWithMaxStringLengthDescription() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay("uri", "operator", true, _stringOfMaxLength()));

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    // python: test_can_add_relay_with_max_string_length_operator
    function test_AddsRelayWithMaxStringLengthOperator() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay("uri", _stringOfMaxLength(), true, "description"));

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    // python: test_cannot_add_relay_with_over_max_string_length_description
    function test_RevertWhen_DescriptionExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay("uri", "operator", true, _stringOverMaxLength()));

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_add_relay_with_over_max_string_length_operator
    function test_RevertWhen_OperatorExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay("uri", _stringOverMaxLength(), true, "description"));

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_add_relay_with_over_max_uri_length
    function test_RevertWhen_UriExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay(_stringOverMaxLength(), "operator", true, "description"));

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    /// @dev python: mev_boost_relay_allowed_list_stub.add_relay(*relay, {"from": owner})
    function _givenRelayAdded(IMEVBoostRelayAllowedList.Relay memory relay) private {
        vm.prank(owner);
        mevBoostRelayAllowedListStub.add_relay(
            relay.uri, relay.operator, relay.is_mandatory, relay.description
        );
    }

    function _givenRelaysAdded(IMEVBoostRelayAllowedList.Relay[] memory relays) private {
        for (uint256 i; i < relays.length; ++i) {
            _givenRelayAdded(relays[i]);
        }
    }

    /// @dev python: "a" * max_string_length
    function _stringOfMaxLength() private pure returns (string memory) {
        return MEVBoostRelays.stringOf("a", MEVBoostRelays.MAX_STRING_LENGTH);
    }

    /// @dev python: "a" * (max_string_length + 1)
    function _stringOverMaxLength() private pure returns (string memory) {
        return MEVBoostRelays.stringOf("a", MEVBoostRelays.MAX_STRING_LENGTH + 1);
    }

    function _relays(IMEVBoostRelayAllowedList.Relay memory relay)
        private
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory relays)
    {
        relays = new IMEVBoostRelayAllowedList.Relay[](1);
        relays[0] = relay;
    }

    function _relays(
        IMEVBoostRelayAllowedList.Relay memory first,
        IMEVBoostRelayAllowedList.Relay memory second
    ) private pure returns (IMEVBoostRelayAllowedList.Relay[] memory relays) {
        relays = new IMEVBoostRelayAllowedList.Relay[](2);
        relays[0] = first;
        relays[1] = second;
    }

    /// @dev python: encode_call_script([(stub, stub.add_relay.encode_input(*relay)) for relay in
    /// relays])
    function _addRelaysScript(IMEVBoostRelayAllowedList.Relay[] memory relays)
        private
        view
        returns (bytes memory)
    {
        bytes[] memory calls = new bytes[](relays.length);

        for (uint256 i; i < relays.length; ++i) {
            calls[i] = MEVBoostRelays.addRelayCallData(relays[i]);
        }

        return EVMScripts.encodeCallScript(address(mevBoostRelayAllowedListStub), calls);
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
