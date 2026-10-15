// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IMEVBoostRelayAllowedList} from "test/foundry/interfaces/External.sol";
import {IMEVBoostRelaysFactory} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `AddMEVBoostRelays`, `RemoveMEVBoostRelays` and `EditMEVBoostRelays`
///         over the live relay allowed list, with the executor as its manager, what the DAO vote
///         sets. The Agent, the list's owner, seeds and cleans up relays around the motions.
contract MEVBoostRelaysAllowedListTest is EasyTrackScenarioBase {
    uint256 private constant MAX_NUM_RELAYS = 40;

    /// @dev python: len(mev_boost_relay_test_config["relays"])
    uint256 private constant RELAYS_COUNT = 3;

    IMEVBoostRelayAllowedList internal allowedList;

    address internal addMEVBoostRelays;
    address internal removeMEVBoostRelays;
    address internal editMEVBoostRelays;

    function setUp() public {
        _forkAndInitialize();

        addMEVBoostRelays = _factoryAddress(config.artifact, "AddMEVBoostRelays");
        IMEVBoostRelaysFactory factory = IMEVBoostRelaysFactory(addMEVBoostRelays);
        allowedList = IMEVBoostRelayAllowedList(factory.mevBoostRelayAllowedList());
        creator = factory.trustedCaller();

        vm.label(addMEVBoostRelays, "AddMEVBoostRelays");
        vm.label(address(allowedList), "MEVBoostRelayAllowedList");
        vm.label(creator, "RMC multisig");

        _registerFactoryIfMissing(
            addMEVBoostRelays,
            abi.encodePacked(allowedList, IMEVBoostRelayAllowedList.add_relay.selector)
        );
        removeMEVBoostRelays = _factory("RemoveMEVBoostRelays");
        _registerFactoryIfMissing(
            removeMEVBoostRelays,
            abi.encodePacked(allowedList, IMEVBoostRelayAllowedList.remove_relay.selector)
        );
        editMEVBoostRelays = _factory("EditMEVBoostRelays");
        _registerFactoryIfMissing(
            editMEVBoostRelays,
            abi.encodePacked(
                allowedList,
                IMEVBoostRelayAllowedList.add_relay.selector,
                allowedList,
                IMEVBoostRelayAllowedList.remove_relay.selector
            )
        );

        // python: setup_script_executor. The vote "Set manager for MEV Boost Relay Allowed List
        // to EVMScriptExecutor", replayed as the owner's call
        _setExecutorAsManager();
    }

    // python: test_add_mev_boost_relays_allowed_list_happy_path
    function testFork_AddRelays() external {
        _makeRoom(RELAYS_COUNT);

        _addByMotion(_relays(1));
        _addByMotion(_relays(RELAYS_COUNT));
    }

    // python: test_add_mev_boost_relays_allowed_list_full_list_happy_path
    function testFork_AddRelaysUpToFullList() external {
        IMEVBoostRelayAllowedList.Relay[] memory current = allowedList.get_relays();
        _removeRelays(current);

        _addByMotion(_padded(current));
    }

    // python: test_remove_mev_boost_relays_allowed_list_happy_path
    function testFork_RemoveRelays() external {
        _removeByMotion(_relays(1));
        _removeByMotion(_relays(RELAYS_COUNT));
    }

    // python: test_remove_mev_boost_relays_allowed_list_full_list_happy_path
    function testFork_RemoveFullList() external {
        _removeByMotion(_padded(allowedList.get_relays()));
    }

    // python: test_edit_mev_boost_relays_allowed_list_happy_path
    function testFork_EditRelays() external {
        IMEVBoostRelayAllowedList.Relay[] memory relays = _relays(RELAYS_COUNT);
        IMEVBoostRelayAllowedList.Relay[] memory modified =
            new IMEVBoostRelayAllowedList.Relay[](RELAYS_COUNT);
        for (uint256 i; i < RELAYS_COUNT; ++i) {
            modified[i] = IMEVBoostRelayAllowedList.Relay({
                uri: relays[i].uri,
                operator: string.concat("op ", vm.toString(i), " updated"),
                is_mandatory: !relays[i].is_mandatory,
                description: relays[i].description
            });
        }

        _editByMotion(_first(relays, 1), _first(modified, 1));
        _editByMotion(relays, modified);
    }

    // --- motion drivers ---

    /// @dev python: create_enact_and_check_add_motion. The relays are absent, a motion adds
    ///      them all, each reads back by its uri, then the Agent removes them again
    function _addByMotion(IMEVBoostRelayAllowedList.Relay[] memory relays) private {
        IMEVBoostRelayAllowedList.Relay[] memory before = allowedList.get_relays();
        for (uint256 i; i < relays.length; ++i) {
            assertFalse(_contains(before, relays[i]), "relay absent before");
        }

        bytes memory callData = abi.encode(relays);

        uint256 motionId = _createMotionCounted(addMEVBoostRelays, callData);
        _executeMotion(motionId, callData);

        IMEVBoostRelayAllowedList.Relay[] memory after_ = allowedList.get_relays();
        assertEq(after_.length, before.length + relays.length, "relays after addition");
        for (uint256 i; i < relays.length; ++i) {
            assertTrue(_contains(after_, relays[i]), "relay present after");
            _assertRelayEq(allowedList.get_relay_by_uri(relays[i].uri), relays[i]);
        }

        _removeRelays(relays);
    }

    /// @dev python: create_enact_and_check_remove_motion. The Agent seeds the relays that are
    ///      absent, a motion removes them all
    function _removeByMotion(IMEVBoostRelayAllowedList.Relay[] memory relays) private {
        _seedRelays(relays);

        IMEVBoostRelayAllowedList.Relay[] memory before = allowedList.get_relays();
        for (uint256 i; i < relays.length; ++i) {
            assertTrue(_contains(before, relays[i]), "relay present before");
        }

        bytes memory callData = abi.encode(_uris(relays));

        uint256 motionId = _createMotionCounted(removeMEVBoostRelays, callData);
        _executeMotion(motionId, callData);

        IMEVBoostRelayAllowedList.Relay[] memory after_ = allowedList.get_relays();
        assertEq(after_.length, before.length - relays.length, "relays after removal");
        for (uint256 i; i < relays.length; ++i) {
            assertFalse(_contains(after_, relays[i]), "relay absent after");
        }
    }

    /// @dev python: create_enact_and_check_edit_motion. The Agent seeds the relays that are
    ///      absent, a motion replaces each by its edited twin of the same uri, the list keeps its
    ///      length, then the Agent removes the uris
    function _editByMotion(
        IMEVBoostRelayAllowedList.Relay[] memory relays,
        IMEVBoostRelayAllowedList.Relay[] memory modified
    ) private {
        assertEq(relays.length, modified.length, "setup: edit pairs");
        for (uint256 i; i < relays.length; ++i) {
            assertEq(relays[i].uri, modified[i].uri, "setup: edit pair uri");
            assertNotEq(_hash(relays[i]), _hash(modified[i]), "setup: edit pair differs");
        }

        _seedRelays(relays);

        IMEVBoostRelayAllowedList.Relay[] memory before = allowedList.get_relays();
        bytes memory callData = abi.encode(modified);

        uint256 motionId = _createMotionCounted(editMEVBoostRelays, callData);
        _executeMotion(motionId, callData);

        IMEVBoostRelayAllowedList.Relay[] memory after_ = allowedList.get_relays();
        assertEq(after_.length, before.length, "relays after edit");
        for (uint256 i; i < relays.length; ++i) {
            assertTrue(_contains(after_, modified[i]), "edited relay present after");
            assertFalse(_contains(after_, relays[i]), "original relay absent after");
            _assertRelayEq(allowedList.get_relay_by_uri(relays[i].uri), modified[i]);
        }

        _removeRelays(relays);
    }

    /// @dev `createMotion` from the trusted multisig, one more motion pending
    function _createMotionCounted(address factory, bytes memory callData)
        private
        returns (uint256 motionId)
    {
        uint256 motionsBefore = easyTrack.getMotions().length;

        motionId = _createMotion(factory, creator, callData);

        assertEq(easyTrack.getMotions().length, motionsBefore + 1, "motions after creation");
    }

    /// @dev python: execute_motion. One motion fewer pending after the enactment
    function _executeMotion(uint256 motionId, bytes memory callData) private {
        uint256 motionsBefore = easyTrack.getMotions().length;

        _enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, motionsBefore - 1, "motions after enactment");
    }

    // --- list state, as the Agent ---

    /// @dev python: setup_script_executor, a no-op when the executor already manages the list
    function _setExecutorAsManager() private {
        if (allowedList.get_manager() == evmScriptExecutor) {
            return;
        }

        vm.prank(allowedList.get_owner());
        allowedList.set_manager(evmScriptExecutor);
    }

    /// @dev Remove the list's first `count` relays when the list is full
    function _makeRoom(uint256 count) private {
        if (allowedList.get_relays_amount() != MAX_NUM_RELAYS) {
            return;
        }

        _removeRelays(_first(allowedList.get_relays(), count));
    }

    /// @dev Add the relays whose uri is absent, each reading back by its uri
    function _seedRelays(IMEVBoostRelayAllowedList.Relay[] memory relays) private {
        IMEVBoostRelayAllowedList.Relay[] memory current = allowedList.get_relays();
        for (uint256 i; i < relays.length; ++i) {
            if (_containsUri(current, relays[i].uri)) {
                continue;
            }

            vm.prank(config.agent);
            allowedList.add_relay(
                relays[i].uri, relays[i].operator, relays[i].is_mandatory, relays[i].description
            );

            _assertRelayEq(allowedList.get_relay_by_uri(relays[i].uri), relays[i]);
        }
    }

    function _removeRelays(IMEVBoostRelayAllowedList.Relay[] memory relays) private {
        for (uint256 i; i < relays.length; ++i) {
            vm.prank(config.agent);
            allowedList.remove_relay(relays[i].uri);
        }
    }

    // --- relays ---

    /// @dev python: mev_boost_relay_test_config["relays"][:count]
    function _relays(uint256 count)
        private
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory relays)
    {
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

        return _first(all, count);
    }

    /// @dev python: the relays_input of the full list tests, `current` padded to the maximum
    ///      with `(f"uri{i}", f"op{i}", True, f"desc{i}")`
    function _padded(IMEVBoostRelayAllowedList.Relay[] memory current)
        private
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory relays)
    {
        relays = new IMEVBoostRelayAllowedList.Relay[](MAX_NUM_RELAYS);
        for (uint256 i; i < current.length; ++i) {
            relays[i] = current[i];
        }

        for (uint256 i = current.length; i < MAX_NUM_RELAYS; ++i) {
            string memory index = vm.toString(i);
            relays[i] = IMEVBoostRelayAllowedList.Relay({
                uri: string.concat("uri", index),
                operator: string.concat("op", index),
                is_mandatory: true,
                description: string.concat("desc", index)
            });
        }
    }

    function _first(IMEVBoostRelayAllowedList.Relay[] memory relays, uint256 count)
        private
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory result)
    {
        result = new IMEVBoostRelayAllowedList.Relay[](count);
        for (uint256 i; i < count; ++i) {
            result[i] = relays[i];
        }
    }

    function _uris(IMEVBoostRelayAllowedList.Relay[] memory relays)
        private
        pure
        returns (string[] memory uris)
    {
        uris = new string[](relays.length);
        for (uint256 i; i < relays.length; ++i) {
            uris[i] = relays[i].uri;
        }
    }

    function _contains(
        IMEVBoostRelayAllowedList.Relay[] memory relays,
        IMEVBoostRelayAllowedList.Relay memory relay
    ) private pure returns (bool) {
        bytes32 hash = _hash(relay);
        for (uint256 i; i < relays.length; ++i) {
            if (_hash(relays[i]) == hash) {
                return true;
            }
        }

        return false;
    }

    function _containsUri(IMEVBoostRelayAllowedList.Relay[] memory relays, string memory uri)
        private
        pure
        returns (bool)
    {
        bytes32 hash = keccak256(bytes(uri));
        for (uint256 i; i < relays.length; ++i) {
            if (keccak256(bytes(relays[i].uri)) == hash) {
                return true;
            }
        }

        return false;
    }

    function _assertRelayEq(
        IMEVBoostRelayAllowedList.Relay memory actual,
        IMEVBoostRelayAllowedList.Relay memory expected
    ) private pure {
        assertEq(actual.uri, expected.uri, "relay uri");
        assertEq(actual.operator, expected.operator, "relay operator");
        assertEq(actual.is_mandatory, expected.is_mandatory, "relay is_mandatory");
        assertEq(actual.description, expected.description, "relay description");
    }

    function _hash(IMEVBoostRelayAllowedList.Relay memory relay) private pure returns (bytes32) {
        return
            keccak256(abi.encode(relay.uri, relay.operator, relay.is_mandatory, relay.description));
    }

    // --- factories ---

    /// @dev A deployed factory trusting the same multisig and targeting the same list as
    ///      `AddMEVBoostRelays`
    function _factory(string memory key) private returns (address factory) {
        factory = _factoryAddress(config.artifact, key);

        vm.label(factory, key);

        assertEq(
            IMEVBoostRelaysFactory(factory).trustedCaller(),
            creator,
            string.concat("setup: ", key, " trustedCaller")
        );
        assertEq(
            IMEVBoostRelaysFactory(factory).mevBoostRelayAllowedList(),
            address(allowedList),
            string.concat("setup: ", key, " mevBoostRelayAllowedList")
        );
    }
}
