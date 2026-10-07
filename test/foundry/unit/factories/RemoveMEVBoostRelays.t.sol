// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {RemoveMEVBoostRelays} from "contracts/EVMScriptFactories/RemoveMEVBoostRelays.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {MEVBoostRelayAllowedListStub} from "contracts/test/MEVBoostRelayAllowedListStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {MEVBoostRelays} from "test/foundry/unit/helpers/MEVBoostRelays.sol";

contract RemoveMEVBoostRelaysTest is Test {
    /// @dev python: range(4) of test_remove_multiple_relays
    uint256 internal constant MULTIPLE_RELAYS_COUNT = 4;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal agent = makeAddr("agent");

    MEVBoostRelayAllowedListStub internal mevBoostRelayAllowedListStub;
    RemoveMEVBoostRelays internal removeMEVBoostRelays;

    function setUp() public {
        mevBoostRelayAllowedListStub = new MEVBoostRelayAllowedListStub(agent, owner);

        vm.prank(owner);
        removeMEVBoostRelays =
            new RemoveMEVBoostRelays(owner, address(mevBoostRelayAllowedListStub));

        vm.label(address(mevBoostRelayAllowedListStub), "mevBoostRelayAllowedListStub");
        vm.label(address(removeMEVBoostRelays), "removeMEVBoostRelays");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(removeMEVBoostRelays.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(removeMEVBoostRelays.mevBoostRelayAllowedList()),
            address(mevBoostRelayAllowedListStub),
            "mevBoostRelayAllowedList"
        );
    }

    // python: test_decode_evm_script_call_data_with_single_relay
    function test_DecodesEVMScriptCallDataWithSingleRelay() external view {
        string[] memory uris = MEVBoostRelays.relayURIs(1);

        string[] memory decoded = removeMEVBoostRelays.decodeEVMScriptCallData(abi.encode(uris));

        assertEq(decoded, uris, "relayURIs");
    }

    // python: test_decode_evm_script_call_data_with_multiple_relays
    function test_DecodesEVMScriptCallDataWithMultipleRelays() external view {
        string[] memory uris = MEVBoostRelays.relayURIs(2);

        string[] memory decoded = removeMEVBoostRelays.decodeEVMScriptCallData(abi.encode(uris));

        assertEq(decoded, uris, "relayURIs");
    }

    // python: test_decode_evm_script_call_data_with_max_relays
    function test_DecodesEVMScriptCallDataWithMaxRelays() external view {
        string[] memory uris = MEVBoostRelays.exampleURIs(MEVBoostRelays.MAX_NUM_RELAYS);

        string[] memory decoded = removeMEVBoostRelays.decodeEVMScriptCallData(abi.encode(uris));

        assertEq(decoded, uris, "relayURIs");
    }

    // python: test_decode_evm_script_call_data_with_empty_calldata
    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        removeMEVBoostRelays.decodeEVMScriptCallData("");
    }

    // python: test_remove_relay
    function test_RemovesRelay() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);
        _addRelays(relays);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), 1, "get_relays_amount");

        string[] memory uris = MEVBoostRelays.urisOf(relays);

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    // python: test_remove_multiple_relays
    function test_RemovesMultipleRelays() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MULTIPLE_RELAYS_COUNT);
        // the Python seeds the first relay twice, the stub has no duplicate check
        _addRelay(relays[0]);
        _addRelays(relays);

        assertEq(
            mevBoostRelayAllowedListStub.get_relays_amount(), relays.length + 1, "get_relays_amount"
        );

        string[] memory uris = MEVBoostRelays.urisOf(relays);

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    // python: test_remove_max_num_relays
    function test_RemovesMaxNumRelays() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);
        _addRelays(relays);

        assertEq(
            mevBoostRelayAllowedListStub.get_relays_amount(),
            MEVBoostRelays.MAX_NUM_RELAYS,
            "get_relays_amount"
        );

        string[] memory uris = MEVBoostRelays.urisOf(relays);

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    // python: test_can_remove_all_relays_in_allow_list
    function test_RemovesAllRelaysInAllowList() external {
        string[] memory uris = MEVBoostRelays.relayURIs(MEVBoostRelays.RELAYS_COUNT);

        // the fixture uris over generated operators and descriptions
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(uris.length);

        for (uint256 i; i < relays.length; ++i) {
            relays[i].uri = uris[i];
        }

        _addRelays(relays);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), uris.length, "get_relays_amount");

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    // python: test_cannot_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        removeMEVBoostRelays.createEVMScript(stranger, "");
    }

    // python: test_cannot_remove_relay_with_empty_calldata
    function test_RevertWhen_RelayUrisAreEmpty() external {
        string[] memory uris = new string[](0);

        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    // python: test_cannot_remove_relay_with_empty_relay_uri
    function test_RevertWhen_RelayUriIsEmpty() external {
        string[] memory uris = _uris("");

        vm.expectRevert("EMPTY_RELAY_URI");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    // python: test_cannot_edit_multiple_relays_when_last_not_in_allow_list
    function test_RevertWhen_LastRelayIsNotInAllowList() external {
        string[] memory uris =
            MEVBoostRelays.exampleURIs(mevBoostRelayAllowedListStub.get_relays_amount() + 1);

        vm.expectRevert("RELAY_NOT_FOUND");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    // python: test_cannot_remove_more_than_max
    function test_RevertWhen_RemovingMoreThanMaxRelays() external {
        string[] memory uris = MEVBoostRelays.exampleURIs(MEVBoostRelays.MAX_NUM_RELAYS + 1);

        vm.expectRevert("RELAY_NOT_FOUND");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    // python: test_cannot_remove_relay_uri_not_in_list
    function test_RevertWhen_RelayUriIsNotInList() external {
        string[] memory uris = MEVBoostRelays.relayURIs(1);

        vm.expectRevert("RELAY_NOT_FOUND");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    // python: test_cannot_remove_relays_with_duplicate_uri
    function test_RevertWhen_RelaysHaveDuplicateUri() external {
        IMEVBoostRelayAllowedList.Relay memory relay = MEVBoostRelays.relayAt(0);
        _addRelay(relay);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), 1, "get_relays_amount");

        string[] memory uris = _uris(relay.uri, relay.uri);

        vm.expectRevert("DUPLICATE_RELAY_URI");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
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

    function _uris(string memory uri) private pure returns (string[] memory uris) {
        uris = new string[](1);
        uris[0] = uri;
    }

    function _uris(string memory first, string memory second)
        private
        pure
        returns (string[] memory uris)
    {
        uris = new string[](2);
        uris[0] = first;
        uris[1] = second;
    }

    /// @dev python: encode_call_script([(stub, stub.remove_relay.encode_input(uri)) for uri in
    /// uris])
    function _removeRelaysScript(string[] memory uris) private view returns (bytes memory) {
        bytes[] memory calls = new bytes[](uris.length);

        for (uint256 i; i < uris.length; ++i) {
            calls[i] = MEVBoostRelays.removeRelayCallData(uris[i]);
        }

        return EVMScripts.encodeCallScript(address(mevBoostRelayAllowedListStub), calls);
    }
}
