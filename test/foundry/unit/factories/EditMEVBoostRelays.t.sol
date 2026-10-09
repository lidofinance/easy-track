// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {EditMEVBoostRelays} from "contracts/EVMScriptFactories/EditMEVBoostRelays.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {MEVBoostRelayAllowedListStub} from "contracts/test/MEVBoostRelayAllowedListStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {MEVBoostRelays} from "test/foundry/unit/helpers/MEVBoostRelays.sol";

contract EditMEVBoostRelaysTest is Test {
    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal agent = makeAddr("agent");

    MEVBoostRelayAllowedListStub internal mevBoostRelayAllowedListStub;
    EditMEVBoostRelays internal editMEVBoostRelays;

    function setUp() public {
        mevBoostRelayAllowedListStub = new MEVBoostRelayAllowedListStub(agent, owner);

        vm.prank(owner);
        editMEVBoostRelays = new EditMEVBoostRelays(owner, address(mevBoostRelayAllowedListStub));

        vm.label(address(mevBoostRelayAllowedListStub), "mevBoostRelayAllowedListStub");
        vm.label(address(editMEVBoostRelays), "editMEVBoostRelays");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(editMEVBoostRelays.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(editMEVBoostRelays.mevBoostRelayAllowedList()),
            address(mevBoostRelayAllowedListStub),
            "mevBoostRelayAllowedList"
        );
    }

    // python: test_decode_evm_script_call_data_single_relay
    function test_DecodesEVMScriptCallDataWithSingleRelay() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            editMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        _assertRelaysEq(decoded, relays);
    }

    // python: test_decode_evm_script_call_data_multiple_relays
    function test_DecodesEVMScriptCallDataWithMultipleRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.relays(MEVBoostRelays.RELAYS_COUNT);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            editMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        _assertRelaysEq(decoded, relays);
    }

    // python: test_edit_single_relay
    function test_EditsSingleRelay() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);
        _addRelays(relays);

        bytes memory evmScript = editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _editRelaysScript(relays), "evmScript");
    }

    // python: test_edit_multiple_relays
    function test_EditsMultipleRelays() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.relays(MEVBoostRelays.RELAYS_COUNT);
        _addRelays(relays);

        bytes memory evmScript = editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _editRelaysScript(relays), "evmScript");
    }

    // python: test_edit_max_num_relays
    function test_EditsMaxNumRelays() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);
        _addRelays(relays);

        bytes memory evmScript = editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _editRelaysScript(relays), "evmScript");
    }

    // python: test_can_edit_relay_and_set_description_to_empty
    function test_EditsRelayAndSetsDescriptionToEmpty() external {
        IMEVBoostRelayAllowedList.Relay memory relay = MEVBoostRelays.relayAt(0);
        _addRelay(relay);

        relay.description = "";
        IMEVBoostRelayAllowedList.Relay[] memory relays = _relays(relay);

        bytes memory evmScript = editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _editRelaysScript(relays), "evmScript");
    }

    // python: test_can_edit_relay_and_set_operator_to_empty
    function test_EditsRelayAndSetsOperatorToEmpty() external {
        IMEVBoostRelayAllowedList.Relay memory relay = MEVBoostRelays.relayAt(0);
        _addRelay(relay);

        relay.operator = "";
        IMEVBoostRelayAllowedList.Relay[] memory relays = _relays(relay);

        bytes memory evmScript = editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _editRelaysScript(relays), "evmScript");
    }

    // python: test_cannot_decode_evm_script_call_data_with_empty_calldata
    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        editMEVBoostRelays.decodeEVMScriptCallData("");
    }

    // python: test_cannot_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        editMEVBoostRelays.createEVMScript(stranger, "");
    }

    // python: test_cannot_edit_relay_with_empty_calldata
    function test_RevertWhen_RelaysAreEmpty() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = new IMEVBoostRelayAllowedList.Relay[](0);

        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_relay_with_empty_uri
    function test_RevertWhen_RelayUriIsEmpty() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            _relays(MEVBoostRelays.relay("", "operator", true, "description"));

        vm.expectRevert("EMPTY_RELAY_URI");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_relay_with_duplicate_uri
    function test_RevertWhen_RelaysHaveDuplicateUri() external {
        string memory uri = MEVBoostRelays.relayAt(0).uri;
        IMEVBoostRelayAllowedList.Relay[] memory relays = _relays(
            MEVBoostRelays.relay(uri, "operator 1", true, "description 1"),
            MEVBoostRelays.relay(uri, "operator 2", false, "description 2")
        );
        _addRelay(relays[0]);

        vm.expectRevert("DUPLICATE_RELAY_URI");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_relay_not_in_allow_list
    function test_RevertWhen_RelayIsNotInAllowList() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);

        vm.expectRevert("RELAY_NOT_FOUND");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_relay_not_in_allow_list_with_multiple_relays
    function test_RevertWhen_RelayIsNotInAllowListWithMultipleRelays() external {
        _addRelays(MEVBoostRelays.relays(1));

        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(2);

        vm.expectRevert("RELAY_NOT_FOUND");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_multiple_relays_when_last_not_in_allow_list
    function test_RevertWhen_LastRelayIsNotInAllowList() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.relays(MEVBoostRelays.RELAYS_COUNT);
        _addRelays(MEVBoostRelays.relays(relays.length - 1));

        assertEq(
            mevBoostRelayAllowedListStub.get_relays_amount(), relays.length - 1, "get_relays_amount"
        );

        vm.expectRevert("RELAY_NOT_FOUND");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_relay_with_uri_over_max_string_length
    function test_RevertWhen_UriExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);

        for (uint256 i; i < relays.length; ++i) {
            relays[i].uri = MEVBoostRelays.stringOf("u", MEVBoostRelays.MAX_STRING_LENGTH + 1);
        }

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_relay_with_operator_over_max_string_length
    function test_RevertWhen_OperatorExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);

        for (uint256 i; i < relays.length; ++i) {
            relays[i].operator = MEVBoostRelays.stringOf("o", MEVBoostRelays.MAX_STRING_LENGTH + 1);
        }

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    // python: test_cannot_edit_relay_with_description_over_max_string_length
    function test_RevertWhen_DescriptionExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);

        for (uint256 i; i < relays.length; ++i) {
            relays[i].description =
                MEVBoostRelays.stringOf("d", MEVBoostRelays.MAX_STRING_LENGTH + 1);
        }

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        editMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    /// @dev python: mev_boost_relay_allowed_list_stub.add_relay(*relay, {"from": owner})
    function _addRelay(IMEVBoostRelayAllowedList.Relay memory relay) private {
        vm.prank(owner);
        mevBoostRelayAllowedListStub.add_relay(
            relay.uri, relay.operator, relay.is_mandatory, relay.description
        );
    }

    function _addRelays(IMEVBoostRelayAllowedList.Relay[] memory relays) private {
        for (uint256 i; i < relays.length; ++i) {
            _addRelay(relays[i]);
        }
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

    /// @dev python: encode_call_script of a remove_relay then an add_relay call per relay, in input
    /// order
    function _editRelaysScript(IMEVBoostRelayAllowedList.Relay[] memory relays)
        private
        view
        returns (bytes memory)
    {
        bytes[] memory calls = new bytes[](relays.length * 2);

        for (uint256 i; i < relays.length; ++i) {
            calls[i * 2] = MEVBoostRelays.removeRelayCallData(relays[i].uri);
            calls[i * 2 + 1] = MEVBoostRelays.addRelayCallData(relays[i]);
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
