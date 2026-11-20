// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice The role ids more than one unit suite grants and checks: the OpenZeppelin AccessControl
/// roles of the Easy Track and the payouts registries, and the Aragon `MANAGE_SIGNING_KEYS` of
/// the node operators registry
library Roles {
    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 internal constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");
    bytes32 internal constant SET_PARAMETERS_ROLE = keccak256("SET_PARAMETERS_ROLE");
    bytes32 internal constant UPDATE_SPENT_AMOUNT_ROLE = keccak256("UPDATE_SPENT_AMOUNT_ROLE");
    bytes32 internal constant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE");
    bytes32 internal constant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE");
    bytes32 internal constant ADD_TOKEN_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_TOKEN_TO_ALLOWED_LIST_ROLE");
    bytes32 internal constant REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE");
}
