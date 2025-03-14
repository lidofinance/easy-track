// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @title Lido's MEV Boost Relay Allowed List interface
interface IMEVBoostRelayAllowedList {
    struct Relay {
        string uri;
        string operator;
        bool is_mandatory;
        string description;
    }

    // View Functions
    function get_relays() external view returns (Relay[] memory);

    // State-Changing Functions
    function add_relay(
        string memory uri,
        string memory operator,
        bool is_mandatory,
        string memory description
    ) external;

    function remove_relay(string memory uri) external;
}
