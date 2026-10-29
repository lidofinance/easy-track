// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {RemoveMEVBoostRelays} from "contracts/EVMScriptFactories/RemoveMEVBoostRelays.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {MEVBoostRelayAllowedListStub} from "contracts/test/MEVBoostRelayAllowedListStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {MEVBoostRelays} from "test/foundry/unit/helpers/MEVBoostRelays.sol";

contract RemoveMEVBoostRelaysTest is Test {
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

    function test_SetsInitialState() external view {
        assertEq(removeMEVBoostRelays.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(removeMEVBoostRelays.mevBoostRelayAllowedList()),
            address(mevBoostRelayAllowedListStub),
            "mevBoostRelayAllowedList"
        );
    }

    function test_DecodesEVMScriptCallDataWithSingleRelay() external view {
        string[] memory uris = MEVBoostRelays.relayURIs(1);

        string[] memory decoded = removeMEVBoostRelays.decodeEVMScriptCallData(abi.encode(uris));

        assertEq(decoded, uris, "relayURIs");
    }

    function test_DecodesEVMScriptCallDataWithMultipleRelays() external view {
        string[] memory uris = MEVBoostRelays.relayURIs(2);

        string[] memory decoded = removeMEVBoostRelays.decodeEVMScriptCallData(abi.encode(uris));

        assertEq(decoded, uris, "relayURIs");
    }

    function test_DecodesEVMScriptCallDataWithMaxRelays() external view {
        string[] memory uris = MEVBoostRelays.exampleURIs(MEVBoostRelays.MAX_NUM_RELAYS);

        string[] memory decoded = removeMEVBoostRelays.decodeEVMScriptCallData(abi.encode(uris));

        assertEq(decoded, uris, "relayURIs");
    }

    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        removeMEVBoostRelays.decodeEVMScriptCallData("");
    }

    function test_RemovesRelay() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);
        MEVBoostRelays.addRelays(mevBoostRelayAllowedListStub, owner, relays);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), 1, "get_relays_amount");

        string[] memory uris = MEVBoostRelays.urisOf(relays);

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    function test_RemovesMultipleRelays() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MULTIPLE_RELAYS_COUNT);
        // the Python seeds the first relay twice, the stub has no duplicate check
        MEVBoostRelays.addRelay(mevBoostRelayAllowedListStub, owner, relays[0]);
        MEVBoostRelays.addRelays(mevBoostRelayAllowedListStub, owner, relays);

        assertEq(
            mevBoostRelayAllowedListStub.get_relays_amount(), relays.length + 1, "get_relays_amount"
        );

        string[] memory uris = MEVBoostRelays.urisOf(relays);

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    function test_RemovesMaxNumRelays() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);
        MEVBoostRelays.addRelays(mevBoostRelayAllowedListStub, owner, relays);

        assertEq(
            mevBoostRelayAllowedListStub.get_relays_amount(),
            MEVBoostRelays.MAX_NUM_RELAYS,
            "get_relays_amount"
        );

        string[] memory uris = MEVBoostRelays.urisOf(relays);

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    function test_RemovesAllRelaysInAllowList() external {
        string[] memory uris = MEVBoostRelays.relayURIs(MEVBoostRelays.RELAYS_COUNT);

        // the fixture uris over generated operators and descriptions
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(uris.length);

        for (uint256 i; i < relays.length; ++i) {
            relays[i].uri = uris[i];
        }

        MEVBoostRelays.addRelays(mevBoostRelayAllowedListStub, owner, relays);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), uris.length, "get_relays_amount");

        bytes memory evmScript = removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));

        assertEq(evmScript, _removeRelaysScript(uris), "evmScript");
    }

    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        removeMEVBoostRelays.createEVMScript(stranger, "");
    }

    function test_RevertWhen_RelayUrisAreEmpty() external {
        string[] memory uris = new string[](0);

        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    function test_RevertWhen_RelayUriIsEmpty() external {
        string[] memory uris = Arrays.list(string(""));

        vm.expectRevert("EMPTY_RELAY_URI");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    function test_RevertWhen_LastRelayIsNotInAllowList() external {
        string[] memory uris =
            MEVBoostRelays.exampleURIs(mevBoostRelayAllowedListStub.get_relays_amount() + 1);

        vm.expectRevert("RELAY_NOT_FOUND");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    function test_RevertWhen_RemovingMoreThanMaxRelays() external {
        string[] memory uris = MEVBoostRelays.exampleURIs(MEVBoostRelays.MAX_NUM_RELAYS + 1);

        vm.expectRevert("RELAY_NOT_FOUND");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    function test_RevertWhen_RelayUriIsNotInList() external {
        string[] memory uris = MEVBoostRelays.relayURIs(1);

        vm.expectRevert("RELAY_NOT_FOUND");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    function test_RevertWhen_RelaysHaveDuplicateUri() external {
        IMEVBoostRelayAllowedList.Relay memory relay = MEVBoostRelays.relayAt(0);
        MEVBoostRelays.addRelay(mevBoostRelayAllowedListStub, owner, relay);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), 1, "get_relays_amount");

        string[] memory uris = Arrays.list(relay.uri, relay.uri);

        vm.expectRevert("DUPLICATE_RELAY_URI");
        removeMEVBoostRelays.createEVMScript(owner, abi.encode(uris));
    }

    function _removeRelaysScript(string[] memory uris) private view returns (bytes memory) {
        bytes[] memory calls = new bytes[](uris.length);

        for (uint256 i; i < uris.length; ++i) {
            calls[i] = MEVBoostRelays.removeRelayCallData(uris[i]);
        }

        return EVMScripts.encodeCallScript(address(mevBoostRelayAllowedListStub), calls);
    }
}
