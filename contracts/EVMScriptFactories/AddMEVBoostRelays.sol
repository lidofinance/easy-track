// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMEVBoostRelayAllowedList.sol";
import "../libraries/MEVBoostRelaysInputUtils.sol";

/// @author katamarinaki, swissarmytowel
/// @notice Creates EVMScript to add new MEV boost relay to MEV Boost relay allowed list
contract AddMEVBoostRelays is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_MAX_NUM_RELAYS_EXCEEDED = "MAX_NUM_RELAYS_EXCEEDED";

    // -------------
    // CONSTANTS
    // -------------

    /// @notice Limit on the number of relays in the registry based on the value from the MEVBoostRelayAllowedList
    uint256 private constant MAX_NUM_RELAYS = 40;

    /// @notice Selector for the add_relay method in the MEVBoostRelayAllowedList
    bytes4 private constant ADD_RELAY_SELECTOR =
        bytes4(keccak256("add_relay(string,string,bool,string)"));

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

    /// @notice Creates EVMScript to add new MEV boost relay to MEV Boost relay allowed list
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded relays data: IMEVBoostRelayAllowedList.Relay[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        IMEVBoostRelayAllowedList.Relay[] memory _relaysToAdd = MEVBoostRelaysInputUtils
            .decodeCallDataWithRelayStructs(_evmScriptCallData);
        IMEVBoostRelayAllowedList.Relay[] memory _currentAllowedRelays = mevBoostRelayAllowedList
            .get_relays();

        require(
            _currentAllowedRelays.length + _relaysToAdd.length <= MAX_NUM_RELAYS,
            ERROR_MAX_NUM_RELAYS_EXCEEDED
        );

        // Validate the input data before creating EVMScript to add new relays. The relay URIs MUST NOT be already in the list.
        MEVBoostRelaysInputUtils.validateRelays(_relaysToAdd, _currentAllowedRelays, false);

        uint256 newRelaysCount = _relaysToAdd.length;
        bytes[] memory encodedCalldata = new bytes[](newRelaysCount);

        for (uint256 i; i < newRelaysCount; ) {
            encodedCalldata[i] = abi.encode(
                _relaysToAdd[i].uri,
                _relaysToAdd[i].operator,
                _relaysToAdd[i].is_mandatory,
                _relaysToAdd[i].description
            );

            unchecked {
                ++i;
            }
        }

        return
            EVMScriptCreator.createEVMScript(
                address(mevBoostRelayAllowedList),
                ADD_RELAY_SELECTOR,
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
