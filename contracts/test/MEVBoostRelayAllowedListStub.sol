// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IMEVBoostRelayAllowedList.sol";

/// @author swissarmytowel
/// @title MEVBoostRelayAllowedListStub
/// @notice Stub implementation of MEVBoostRelayAllowedList for testing purposes only
contract MEVBoostRelayAllowedListStub is IMEVBoostRelayAllowedList {
    Relay[] internal relays;

    address internal owner;
    address internal manager;

    // Constructor

    constructor(address _owner, address _manager) {
        owner = _owner;
        manager = _manager;
    }

    // State-Changing Functions

    function add_relay(
        string memory uri,
        string memory operator,
        bool is_mandatory,
        string memory description
    ) external override {
        require(msg.sender == owner || msg.sender == manager, "NOT_AUTHORIZED");
        relays.push(Relay(uri, operator, is_mandatory, description));
    }

    function remove_relay(string memory uri) external override {
        require(msg.sender == owner || msg.sender == manager, "NOT_AUTHORIZED");
        for (uint256 i = 0; i < relays.length; i++) {
            if (keccak256(abi.encodePacked(relays[i].uri)) == keccak256(abi.encodePacked(uri))) {
                relays[i] = relays[relays.length - 1];
                relays.pop();
                break;
            }
        }
    }

    function set_owner(address _owner) external {
        owner = _owner;
    }

    function set_manager(address _manager) external {
        manager = _manager;
    }

    // View Functions

    function get_relays() external view override returns (Relay[] memory) {
        return relays;
    }

    function get_relay_by_uri(string memory uri) external view returns (Relay memory) {
        for (uint256 i = 0; i < relays.length; i++) {
            if (keccak256(abi.encodePacked(relays[i].uri)) == keccak256(abi.encodePacked(uri))) {
                return relays[i];
            }
        }
        revert("RELAY_NOT_FOUND");
    }

    function get_relays_amount() external view returns (uint256) {
        return relays.length;
    }

    function get_owner() external view returns (address) {
        return owner;
    }

    function get_manager() external view returns (address) {
        return manager;
    }
}
