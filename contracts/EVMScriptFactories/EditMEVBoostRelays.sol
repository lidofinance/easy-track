// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMEVBoostRelayAllowedList.sol";
import "../libraries/MEVBoostRelaysInputUtils.sol";

/// @author katamarinaki, swissarmytowel
/// @notice Creates EVMScript to edit MEV boost relays in the MEV Boost Relay allow list by the URI
contract EditMEVBoostRelays is TrustedCaller, IEVMScriptFactory {
    // -------------
    // CONSTANTS
    // -------------

    /// @notice Selector for the add_relay method in the MEVBoostRelayAllowedList
    bytes4 private constant ADD_RELAY_SELECTOR =
        bytes4(keccak256("add_relay(string,string,bool,string)"));
    /// @notice Selector for the remove_relay method in the MEVBoostRelayAllowedList
    bytes4 private constant REMOVE_RELAY_SELECTOR = bytes4(keccak256("remove_relay(string)"));

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the MEVBoostRelayAllowedList contract
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

    /// @notice Creates EVMScript to edit a MEV boost relay in the MEV Boost relay allow list by the URI
    /// @dev Edit operation is achieved by removing the updated relay from the list and adding it back with the new parameters
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded relays data: IMEVBoostRelayAllowedList.Relay[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        IMEVBoostRelayAllowedList.Relay[] memory _relaysToEdit = MEVBoostRelaysInputUtils
            .decodeCallDataWithRelayStructs(_evmScriptCallData);
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays = mevBoostRelayAllowedList
            .get_relays();

        // Validate input data before creating EVMScript to edit relays. The relay URIs MUST be already in the list.
        MEVBoostRelaysInputUtils.validateRelays(_relaysToEdit, _currentAllowedRelays, true);

        // Allocate 2x the length of the decoded call data for the methodIds and encodedCalldata arrays
        // as each relay edit requires two relay calls (remove and add)
        uint256 editRelaysCount = _relaysToEdit.length;
        bytes4[] memory methodIds = new bytes4[](editRelaysCount * 2);
        bytes[] memory encodedCalldata = new bytes[](editRelaysCount * 2);

        // Iterate over the decoded call data and create the methodIds and encodedCalldata
        // allowed list contract does not allow edits, so they are achieved by stacking remove and add relay calls on i and i + 1 positions
        // of the methodIds and encodedCalldata arrays respectively
        for (uint256 i; i < editRelaysCount; ) {
            uint256 index = i * 2;

            // Remove relay by uri from the registry
            methodIds[index] = REMOVE_RELAY_SELECTOR;
            encodedCalldata[index] = abi.encode(_relaysToEdit[i].uri);

            // Add relay to the registry with the new parameters and same uri
            methodIds[index + 1] = ADD_RELAY_SELECTOR;
            encodedCalldata[index + 1] = abi.encode(
                _relaysToEdit[i].uri,
                _relaysToEdit[i].operator,
                _relaysToEdit[i].is_mandatory,
                _relaysToEdit[i].description
            );

            unchecked {
                ++i;
            }
        }

        return
            EVMScriptCreator.createEVMScript(
                address(mevBoostRelayAllowedList),
                methodIds,
                encodedCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded relays data: IMEVBoostRelayAllowedList.Relay[]
    /// @return relays IMEVBoostRelayAllowedList.Relay[]
    function decodeEVMScriptCallData(
        bytes calldata _evmScriptCallData
    ) external pure returns (IMEVBoostRelayAllowedList.Relay[] memory relays) {
        return MEVBoostRelaysInputUtils.decodeCallDataWithRelayStructs(_evmScriptCallData);
    }
}
