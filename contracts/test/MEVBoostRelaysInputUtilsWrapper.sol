// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../libraries/MEVBoostRelaysInputUtils.sol";

contract MEVBoostRelaysInputUtilsWrapper {
    function decodeCallDataWithRelayStructs(
        bytes memory _evmScriptCallData
    ) external pure returns (IMEVBoostRelayAllowedList.Relay[] memory) {
        return MEVBoostRelaysInputUtils.decodeCallDataWithRelayStructs(_evmScriptCallData);
    }

    function decodeCallDataWithRelayURIs(
        bytes memory _relayData
    ) external pure returns (string[] memory) {
        return MEVBoostRelaysInputUtils.decodeCallDataWithRelayURIs(_relayData);
    }

    function validateRelays(
        string[] memory _relayURIs,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays,
        bool _shouldExist
    ) external pure {
        MEVBoostRelaysInputUtils.validateRelays(_relayURIs, _currentAllowedRelays, _shouldExist);
    }

    function validateRelays(
        IMEVBoostRelayAllowedList.Relay[] memory _relays,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays,
        bool _shouldExist
    ) external pure {
        MEVBoostRelaysInputUtils.validateRelays(_relays, _currentAllowedRelays, _shouldExist);
    }
}
