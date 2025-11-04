// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @title Lido's Validators Exit Bus Oracle Interface
interface IValidatorsExitBusOracle {
    function submitExitRequestsHash(bytes32 exitRequestsHash) external;
}
