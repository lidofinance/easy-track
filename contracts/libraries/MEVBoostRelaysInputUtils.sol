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
    /// @param _expectExistence Switches the expected existence of the relay URIs in the current relay list
    ///                         if true, the relay URIs should exist in the current relay list and will revert otherwise
    ///                         if false, the relay URIs should NOT exist in the current relay list and will revert otherwise
    function validateRelays(
        IMEVBoostRelayAllowedList.Relay[] memory _relays,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays,
        bool _expectExistence
    ) internal pure {
        uint256 relaysCount = _relays.length;

        require(relaysCount > 0, ERROR_EMPTY_RELAYS_ARRAY);

        for (uint256 i; i < relaysCount; ) {
            IMEVBoostRelayAllowedList.Relay memory relay = _relays[i];
            // Validate the Relay parameters: URI, operator, and description
            uint256 relayURILength = bytes(relay.uri).length;

            require(relayURILength > 0, ERROR_EMPTY_RELAY_URI);
            require(relayURILength <= MAX_STRING_LENGTH, ERROR_MAX_STRING_LENGTH_EXCEEDED);
            require(
                bytes(relay.operator).length <= MAX_STRING_LENGTH,
                ERROR_MAX_STRING_LENGTH_EXCEEDED
            );
            require(
                bytes(relay.description).length <= MAX_STRING_LENGTH,
                ERROR_MAX_STRING_LENGTH_EXCEEDED
            );

            _validateNoDuplicateInputFromIndex(i, _relays);

            bool relayExistsInList = _isRelayURIContained(
                bytes(_relays[i].uri),
                _currentAllowedRelays
            );

            if (_expectExistence) {
                require(relayExistsInList, ERROR_RELAY_NOT_FOUND);
            } else {
                require(!relayExistsInList, ERROR_RELAY_URI_ALREADY_EXISTS);
            }

            unchecked {
                ++i;
            }
        }
    }

    /// @notice Validates an array of relays by their URI strings
    /// @param _relayURIs Array of Relay URI strings to validate
    /// @param _currentAllowedRelays Current list of allowed relays from the MEVBoostRelayAllowedList contract
    function validateRelayURIs(
        string[] memory _relayURIs,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays
    ) internal pure {
        require(_relayURIs.length > 0, ERROR_EMPTY_RELAYS_ARRAY);

        uint256 relayURIsCount = _relayURIs.length;

        for (uint256 i; i < relayURIsCount; ) {
            bytes memory uri = bytes(_relayURIs[i]);

            // Validate the URI length and presence
            require(uri.length > 0, ERROR_EMPTY_RELAY_URI);
            require(uri.length <= MAX_STRING_LENGTH, ERROR_MAX_STRING_LENGTH_EXCEEDED);

            _validateNoDuplicateInputFromIndex(i, _relayURIs);

            bool relayExistsInList = _isRelayURIContained(uri, _currentAllowedRelays);
            // This validation is only used for removing relays, so the relay should exist in the list
            require(relayExistsInList, ERROR_RELAY_NOT_FOUND);

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

    /// @dev Asserts that a relay URI exists or not in the current relay list according to the expected condition
    function _isRelayURIContained(
        bytes memory _uri,
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays
    ) private pure returns (bool exists) {
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
    }

    /// @dev Checks for duplicate URIs in a string array of URIs
    ///      Starts checking from the current relay index to optimize gas usage
    function _validateNoDuplicateInputFromIndex(
        uint256 _currentRelayIndex,
        string[] memory _relayURIs
    ) private pure {
        bytes32 currentURIHash = keccak256(bytes(_relayURIs[_currentRelayIndex]));

        for (uint256 i = _currentRelayIndex + 1; i < _relayURIs.length; ) {
            require(keccak256(bytes(_relayURIs[i])) != currentURIHash, ERROR_DUPLICATE_RELAY_URI);

            unchecked {
                ++i;
            }
        }
    }

    /// @dev Checks for duplicate URIs in a Relay struct array
    ///      Starts checking from the current relay index to optimize gas usage
    function _validateNoDuplicateInputFromIndex(
        uint256 _currentRelayIndex,
        IMEVBoostRelayAllowedList.Relay[] memory _relays
    ) private pure {
        bytes32 currentURIHash = keccak256(bytes(_relays[_currentRelayIndex].uri));

        for (uint256 i = _currentRelayIndex + 1; i < _relays.length; ) {
            require(keccak256(bytes(_relays[i].uri)) != currentURIHash, ERROR_DUPLICATE_RELAY_URI);

            unchecked {
                ++i;
            }
        }
    }
}
