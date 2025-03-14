// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMEVBoostRelayAllowedList.sol";
import "../libraries/MEVBoostRelaysInputUtils.sol";

/// @author katamarinaki, swissarmytowel
/// @notice Creates EVMScript to remove a MEV boost relay from the MEV Boost relay allow list
contract RemoveMEVBoostRelays is TrustedCaller, IEVMScriptFactory {
    // -------------
    // CONSTANTS
    // -------------

    /// @notice Selector for the remove_relay method in the MEVBoostRelayAllowedList
    bytes4 private constant REMOVE_RELAY_SELECTOR = bytes4(keccak256("remove_relay(string)"));

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of MEVBoostRelayAllowedList contract
    IMEVBoostRelayAllowedList public immutable mevBoostRelayAllowedList;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _mevBoostRelayAllowedList
    ) TrustedCaller(_trustedCaller) {
        mevBoostRelayAllowedList = IMEVBoostRelayAllowedList(_mevBoostRelayAllowedList);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to remove a MEV boost relay from MEV Boost relay allow list
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded relay URIs: string[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        // Decode the input data to get the relays to remove
        string[] memory _relayURIsToRemove = MEVBoostRelaysInputUtils.decodeCallDataWithRelayURIs(
            _evmScriptCallData
        );
        // Get the current list of allowed relays from the MEVBoostRelayAllowedList contract
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays = mevBoostRelayAllowedList
            .get_relays();

        // Validate input data before creating EVMScript to remove relays.  The relay URIs MUST be already in the list.
        MEVBoostRelaysInputUtils.validateRelays(_relayURIsToRemove, _currentAllowedRelays, true);

        uint256 removeRelaysCount = _relayURIsToRemove.length;
        bytes[] memory encodedCalldata = new bytes[](removeRelaysCount);

        for (uint256 i; i < removeRelaysCount; ) {
            encodedCalldata[i] = abi.encode(_relayURIsToRemove[i]);

            unchecked {
                ++i;
            }
        }

        return
            EVMScriptCreator.createEVMScript(
                address(mevBoostRelayAllowedList),
                REMOVE_RELAY_SELECTOR,
                encodedCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded relay URIs: string[]
    /// @return relayUris string[]
    function decodeEVMScriptCallData(
        bytes calldata _evmScriptCallData
    ) external pure returns (string[] memory relayUris) {
        return MEVBoostRelaysInputUtils.decodeCallDataWithRelayURIs(_evmScriptCallData);
    }
}
