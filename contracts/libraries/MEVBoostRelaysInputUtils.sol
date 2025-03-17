// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IMEVBoostRelayAllowedList.sol";

/// @author swissarmytowel
/// @notice Utility functions for validating and decoding MEV Boost relay input data
library MEVBoostRelaysInputUtils {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_EMPTY_RELAYS_ARRAY = "EMPTY_RELAYS_ARRAY";
    string private constant ERROR_EMPTY_RELAY_URI = "EMPTY_RELAY_URI";
    string private constant ERROR_MAX_STRING_LENGTH_EXCEEDED = "MAX_STRING_LENGTH_EXCEEDED";
    string private constant ERROR_RELAY_URI_ALREADY_EXISTS = "RELAY_URI_ALREADY_EXISTS";
    string private constant ERROR_RELAY_NOT_FOUND = "RELAY_NOT_FOUND";
    string private constant ERROR_DUPLICATE_RELAY_URI = "DUPLICATE_RELAY_URI";

    // -------------
    // CONSTANTS
    // -------------

    /// @notice Maximum length of a string defined in the MEVBoostRelayAllowedList contract
    uint256 private constant MAX_STRING_LENGTH = 1024;

    // ========================================================
    // Dedicated Validation Functions for Each Operation
    // ========================================================

    /// @notice Validates an array of relay structs
    /// @param _relays Array of Relay structs to validate
    /// @param _currentAllowedRelays Current list of allowed relays from the MEVBoostRelayAllowedList contract
    /// @param _shouldExist Whether the relay URIs should exist or not in the current relay list
    function validateRelays(
        IMEVBoostRelayAllowedList.Relay[] memory _relays,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays,
        bool _shouldExist
    ) internal pure {
        require(_relays.length > 0, ERROR_EMPTY_RELAYS_ARRAY);

        uint256 relaysCount = _relays.length;

        for (uint256 i; i < relaysCount; ) {
            // Validate the Relay parameters: URI, operator, and description
            _validateRelayParameters(_relays[i]);
            _validateNoDuplicateInput(i, _relays);
            _validateRelayUriPresence(bytes(_relays[i].uri), _currentAllowedRelays, _shouldExist);

            unchecked {
                ++i;
            }
        }
    }

    /// @notice Validates an array of relays by their URI strings
    /// @param _relayURIs Array of Relay URI strings to validate
    /// @param _currentAllowedRelays Current list of allowed relays from the MEVBoostRelayAllowedList contract
    /// @param _shouldExist Whether the relay URIs should exist or not in the current relay list
    function validateRelays(
        string[] memory _relayURIs,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays,
        bool _shouldExist
    ) internal pure {
        require(_relayURIs.length > 0, ERROR_EMPTY_RELAYS_ARRAY);

        uint256 relayURIsCount = _relayURIs.length;

        for (uint256 i; i < relayURIsCount; ) {
            bytes memory uri = bytes(_relayURIs[i]);

            // Validate the URI length and presence
            _validateUriString(uri);
            _validateNoDuplicateInput(i, _relayURIs);
            _validateRelayUriPresence(uri, _currentAllowedRelays, _shouldExist);

            unchecked {
                ++i;
            }
        }
    }

    /// @notice Decodes the call data for a relay struct array
    /// @param _evmScriptCallData Encoded relay struct array
    /// @return Array of Relay structs decoded from the call data
    function decodeCallDataWithRelayStructs(
        bytes memory _evmScriptCallData
    ) internal pure returns (IMEVBoostRelayAllowedList.Relay[] memory) {
        return abi.decode(_evmScriptCallData, (IMEVBoostRelayAllowedList.Relay[]));
    }

    /// @notice Decodes the call data for a relay URI string array
    /// @param _evmScriptCallData Encoded relay URI string array
    /// @return Array of relay URIs decoded from the call data
    function decodeCallDataWithRelayURIs(
        bytes memory _evmScriptCallData
    ) internal pure returns (string[] memory) {
        return abi.decode(_evmScriptCallData, (string[]));
    }

    // ========================================================
    // Private Helper Functions
    // ========================================================

    /// @dev Validates Relay parameters: URI, operator, and description
    function _validateRelayParameters(IMEVBoostRelayAllowedList.Relay memory _relay) private pure {
        _validateUriString(bytes(_relay.uri));

        _validateStringLengthLimit(bytes(_relay.operator));
        _validateStringLengthLimit(bytes(_relay.description));
    }

    /// @dev Validates the URI length and presence
    function _validateUriString(bytes memory _uri) private pure {
        require(_uri.length > 0, ERROR_EMPTY_RELAY_URI);

        _validateStringLengthLimit(_uri);
    }

    /// @dev Asserts that a relay URI exists or not in the current relay list according to the expected condition
    function _validateRelayUriPresence(
        bytes memory _uri,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays,
        bool _shouldExist
    ) private pure {
        bool exists;
        uint256 currentAllowedRelaysLength = _currentAllowedRelays.length;
        bytes32 uriHash = keccak256(_uri);

        for (uint256 j; j < currentAllowedRelaysLength; ) {
            if (keccak256(bytes(_currentAllowedRelays[j].uri)) == uriHash) {
                exists = true;
                break;
            }

            unchecked {
                ++j;
            }
        }

        if (_shouldExist) {
            require(exists, ERROR_RELAY_NOT_FOUND);
        } else {
            require(!exists, ERROR_RELAY_URI_ALREADY_EXISTS);
        }
    }

    /// @dev Checks for duplicate URIs in a string array of URIs
    ///      Starts checking from the current relay index to optimize gas usage
    function _validateNoDuplicateInput(
        uint256 _currentRelayIndex,
        string[] memory _relayURIs
    ) private pure {
        bytes32 currentUriHash = keccak256(bytes(_relayURIs[_currentRelayIndex]));

        for (uint256 i = _currentRelayIndex + 1; i < _relayURIs.length; ) {
            require(keccak256(bytes(_relayURIs[i])) != currentUriHash, ERROR_DUPLICATE_RELAY_URI);

            unchecked {
                ++i;
            }
        }
    }

    /// @dev Checks for duplicate URIs in a Relay struct array
    ///      Starts checking from the current relay index to optimize gas usage
    function _validateNoDuplicateInput(
        uint256 _currentRelayIndex,
        IMEVBoostRelayAllowedList.Relay[] memory _relays
    ) private pure {
        bytes32 currentUriHash = keccak256(bytes(_relays[_currentRelayIndex].uri));

        for (uint256 i = _currentRelayIndex + 1; i < _relays.length; ) {
            require(keccak256(bytes(_relays[i].uri)) != currentUriHash, ERROR_DUPLICATE_RELAY_URI);

            unchecked {
                ++i;
            }
        }
    }

    /// @dev Validates the length of a string does not exceed the maximum allowed
    function _validateStringLengthLimit(bytes memory _string) private pure {
        require(_string.length <= MAX_STRING_LENGTH, ERROR_MAX_STRING_LENGTH_EXCEEDED);
    }
}
