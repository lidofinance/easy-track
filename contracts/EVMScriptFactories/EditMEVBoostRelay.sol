// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMEVBoostRelayAllowedList.sol";

/// @author swissarmytowel
/// @notice Creates EVMScript to edit MEV boost relays in the MEV Boost Relay allow list by the URI
contract EditMEVBoostRelay is TrustedCaller, IEVMScriptFactory {
    struct EditMEVBoostRelayInput {
        // key to identify the relay
        string uri;
        // relay parameters
        string operator;
        bool is_mandatory;
        string description;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";
    string private constant ERROR_RELAYS_COUNT_MISMATCH = "RELAYS_COUNT_MISMATCH";
    string private constant ERROR_MAX_NUM_RELAYS_EXCEEDED = "MAX_NUM_RELAYS_EXCEEDED";
    string private constant ERROR_EMPTY_RELAY_URI = "EMPTY_RELAY_URI";
    string private constant ERROR_RELAY_NOT_FOUND = "RELAY_NOT_FOUND";

    // -------------
    // CONSTANTS
    // -------------

    /// @dev selector for the add_relay method in the MEVBoostRelayAllowedList
    bytes4 private constant ADD_RELAY_SELECTOR =
        bytes4(keccak256("add_relay(string,string,bool,string)"));
    /// @dev selector for the remove_relay method in the MEVBoostRelayAllowedList
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

    /// @notice Creates EVMScript to edit a MEV boost relay in the MEV Boost relay allow list by the URI
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: EditMEVBoostRelayInput[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        (
            uint256 relaysCount,
            EditMEVBoostRelayInput[] memory decodedCallData
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        uint256 decodedCalldataLength = decodedCallData.length;

        bytes4[] memory methodIds = new bytes4[](decodedCalldataLength * 2);
        bytes[] memory encodedCalldata = new bytes[](decodedCalldataLength * 2);

        _validateInputData(relaysCount, decodedCallData);

        // iterate over the decoded call data and create the methodIds and encodedCalldata
        // allow list does not allow edits, so they are achieved by stacking remove and add relay calls on i and i + 1 positions
        // of the methodIds and encodedCalldata arrays respectively
        for (uint256 i; i < decodedCalldataLength; ) {
            uint256 index = i * 2;

            // remove relay by uri from the registry
            methodIds[index] = REMOVE_RELAY_SELECTOR;
            encodedCalldata[index] = abi.encode(decodedCallData[i].uri);

            // add relay to the registry with the new parameters and same uri
            methodIds[index + 1] = ADD_RELAY_SELECTOR;
            encodedCalldata[index + 1] = abi.encode(
                decodedCallData[i].uri,
                decodedCallData[i].operator,
                decodedCallData[i].is_mandatory,
                decodedCallData[i].description
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
    /// @param _evmScriptCallData Encoded (uint256, EditMEVBoostRelayInput[])
    /// @return relaysCount current number of relays in allowed list
    /// @return relays EditMEVBoostRelayInput[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (uint256 relaysCount, EditMEVBoostRelayInput[] memory relays) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (uint256 relaysCount, EditMEVBoostRelayInput[] memory relays) {
        (relaysCount, relays) = abi.decode(_evmScriptCallData, (uint256, EditMEVBoostRelayInput[]));
    }

    function _validateInputData(
        uint256 _relaysCount,
        EditMEVBoostRelayInput[] memory _relayInputs
    ) private view {
        uint256 calldataLength = _relayInputs.length;

        require(calldataLength > 0, ERROR_EMPTY_CALLDATA);

        require(
            mevBoostRelayAllowedList.get_relays_amount() == _relaysCount,
            ERROR_RELAYS_COUNT_MISMATCH
        );

        for (uint256 i; i < calldataLength; ) {
            string memory uri = _relayInputs[i].uri;
            require(bytes(uri).length > 0, ERROR_EMPTY_RELAY_URI);

            // check if relay with the given uri exists, if not, the relay cannot be edited
            require(relayURIExists(uri), ERROR_RELAY_NOT_FOUND);

            unchecked {
                ++i;
            }
        }
    }

    function relayURIExists(string memory uri) private view returns (bool) {
        try mevBoostRelayAllowedList.get_relay_by_uri(uri) returns (
            IMEVBoostRelayAllowedList.Relay memory
        ) {
            return true;
        } catch {
            return false;
        }
    }
}
