// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AddMEVBoostRelays} from "contracts/EVMScriptFactories/AddMEVBoostRelays.sol";
import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {MEVBoostRelayAllowedListStub} from "contracts/test/MEVBoostRelayAllowedListStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
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

    function test_SetsInitialState() external view {
        assertEq(addMEVBoostRelays.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(addMEVBoostRelays.mevBoostRelayAllowedList()),
            address(mevBoostRelayAllowedListStub),
            "mevBoostRelayAllowedList"
        );
    }

    function test_DecodesEVMScriptCallDataWithSingleRelay() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            addMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        MEVBoostRelays.assertRelaysEq(decoded, relays);
    }

    function test_DecodesEVMScriptCallDataWithMultipleRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(2);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            addMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        MEVBoostRelays.assertRelaysEq(decoded, relays);
    }

    function test_DecodesEVMScriptCallDataWithMaxRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);

        IMEVBoostRelayAllowedList.Relay[] memory decoded =
            addMEVBoostRelays.decodeEVMScriptCallData(abi.encode(relays));

        MEVBoostRelays.assertRelaysEq(decoded, relays);
    }

    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        addMEVBoostRelays.decodeEVMScriptCallData("");
    }

    function test_CreatesEVMScriptWithOneRelay() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = MEVBoostRelays.relays(1);

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    function test_CreatesEVMScriptWithMultipleRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.relays(MEVBoostRelays.RELAYS_COUNT);

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    function test_AddsMaxNumRelays() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS);

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        addMEVBoostRelays.createEVMScript(stranger, "");
    }

    function test_RevertWhen_RelaysAreEmpty() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = new IMEVBoostRelayAllowedList.Relay[](0);

        vm.expectRevert("EMPTY_RELAYS_ARRAY");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    function test_RevertWhen_RelayUriIsEmpty() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            Arrays.list(MEVBoostRelays.relay("", "operator", true, "description"));

        vm.expectRevert("EMPTY_RELAY_URI");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    function test_RevertWhen_AddingMoreRelaysThanAllowed() external {
        MEVBoostRelays.addRelays(
            mevBoostRelayAllowedListStub,
            owner,
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS)
        );

        vm.expectRevert("MAX_NUM_RELAYS_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(MEVBoostRelays.relays(1)));
    }

    function test_RevertWhen_BatchAddingMoreRelaysThanAllowed() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            MEVBoostRelays.generatedRelays(MEVBoostRelays.MAX_NUM_RELAYS + 1);

        vm.expectRevert("MAX_NUM_RELAYS_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    function test_RevertWhen_RelayUriAlreadyExists() external {
        IMEVBoostRelayAllowedList.Relay memory relay = MEVBoostRelays.relayAt(0);
        MEVBoostRelays.addRelay(mevBoostRelayAllowedListStub, owner, relay);

        assertEq(mevBoostRelayAllowedListStub.get_relays_amount(), 1, "get_relays_amount");
        assertEq(mevBoostRelayAllowedListStub.get_relay_by_uri(relay.uri).uri, relay.uri, "uri");

        vm.expectRevert("RELAY_URI_ALREADY_EXISTS");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(Arrays.list(relay)));
    }

    function test_RevertWhen_RelaysHaveDuplicateUri() external {
        IMEVBoostRelayAllowedList.Relay memory duplicate = MEVBoostRelays.relayAt(1);
        duplicate.uri = MEVBoostRelays.relayAt(0).uri;

        IMEVBoostRelayAllowedList.Relay[] memory relays =
            Arrays.list(MEVBoostRelays.relayAt(0), duplicate);

        vm.expectRevert("DUPLICATE_RELAY_URI");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    function test_AddsRelayWithMaxUriLength() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays = Arrays.list(
            MEVBoostRelays.relay(_stringOfMaxLength(), "operator", true, "description")
        );

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    function test_AddsRelayWithMaxStringLengthDescription() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            Arrays.list(MEVBoostRelays.relay("uri", "operator", true, _stringOfMaxLength()));

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    function test_AddsRelayWithMaxStringLengthOperator() external view {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            Arrays.list(MEVBoostRelays.relay("uri", _stringOfMaxLength(), true, "description"));

        bytes memory evmScript = addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));

        assertEq(evmScript, _addRelaysScript(relays), "evmScript");
    }

    function test_RevertWhen_DescriptionExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            Arrays.list(MEVBoostRelays.relay("uri", "operator", true, _stringOverMaxLength()));

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    function test_RevertWhen_OperatorExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays =
            Arrays.list(MEVBoostRelays.relay("uri", _stringOverMaxLength(), true, "description"));

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    function test_RevertWhen_UriExceedsMaxStringLength() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = Arrays.list(
            MEVBoostRelays.relay(_stringOverMaxLength(), "operator", true, "description")
        );

        vm.expectRevert("MAX_STRING_LENGTH_EXCEEDED");
        addMEVBoostRelays.createEVMScript(owner, abi.encode(relays));
    }

    function _stringOfMaxLength() private pure returns (string memory) {
        return MEVBoostRelays.stringOf("a", MEVBoostRelays.MAX_STRING_LENGTH);
    }

    function _stringOverMaxLength() private pure returns (string memory) {
        return MEVBoostRelays.stringOf("a", MEVBoostRelays.MAX_STRING_LENGTH + 1);
    }

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
}
