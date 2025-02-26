// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMEVBoostRelayAllowedList.sol";

/// @author katamarinaki
/// @notice Creates EVMScript to add new MEV boost relay to MEV Boost relay allow list
contract AddMEVBoostRelay is TrustedCaller, IEVMScriptFactory {
    /// @notice Input data for createEVMScript method to add new MEV boost relay, has the same structure as Relay struct in MEVBoostRelayAllowedList
    struct AddMEVBoostRelayInput {
        string uri;
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
    string private constant ERROR_RELAY_URI_ALREADY_EXISTS = "RELAY_URI_ALREADY_EXISTS";
    string private constant ERROR_RELAY_URI_DUPLICATE = "RELAY_URI_HAS_A_DUPLICATE";

    // -------------
    // CONSTANTS
    // -------------

    /// @notice limits the number of relays in the registry based on the value from the MEVBoostRelayAllowedList
    uint256 private constant MAX_NUM_RELAYS = 40;
    /// @notice selector for the add_relay method in the MEVBoostRelayAllowedList
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

    /// @notice Creates EVMScript to add new MEV boost relay to MEV Boost relay allow list
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded relays count and new data: (uint256, AddMEVBoostRelayInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        (
            uint256 relaysCount,
            AddMEVBoostRelayInput[] memory decodedCallData
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        uint256 calldataLength = decodedCallData.length;

        // validate input data
        require(calldataLength > 0, ERROR_EMPTY_CALLDATA);
        require(
            mevBoostRelayAllowedList.get_relays_amount() == relaysCount,
            ERROR_RELAYS_COUNT_MISMATCH
        );
        require(relaysCount + calldataLength <= MAX_NUM_RELAYS, ERROR_MAX_NUM_RELAYS_EXCEEDED);

        bytes4[] memory methodIds = new bytes4[](calldataLength);
        bytes[] memory encodedCalldata = new bytes[](calldataLength);

        for (uint256 i; i < calldataLength; ) {
            _validateRelayURI(decodedCallData[i].uri, i, decodedCallData);

            // check duplicates
            methodIds[i] = ADD_RELAY_SELECTOR;
            encodedCalldata[i] = abi.encode(
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
    /// @param _evmScriptCallData Encoded relays count and new data: (uint256, AddMEVBoostRelayInput[])
    /// @return relaysCount current number of relays in allowed list
    /// @return relays AddMEVBoostRelayInput[]
    function decodeEVMScriptCallData(
        bytes calldata _evmScriptCallData
    ) external pure returns (uint256 relaysCount, AddMEVBoostRelayInput[] memory relays) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (uint256 relaysCount, AddMEVBoostRelayInput[] memory relays) {
        (relaysCount, relays) = abi.decode(_evmScriptCallData, (uint256, AddMEVBoostRelayInput[]));
    }

    function _validateRelayURI(
        string memory _relayInputURI,
        uint256 _currentIndex,
        AddMEVBoostRelayInput[] memory _relays
    ) private view {
        require(bytes(_relayInputURI).length > 0, ERROR_EMPTY_RELAY_URI);
        require(isRelayUriAvailable(_relayInputURI), ERROR_RELAY_URI_ALREADY_EXISTS);

        // check for duplicates in the input data array, starting from the current index for efficiency
        // if a duplicate is found, it will throw an exception
        for (uint256 i = _currentIndex; i < _relays.length; ) {
            require(
                keccak256(bytes(_relays[i].uri)) != keccak256(bytes(_relayInputURI)),
                ERROR_RELAY_URI_DUPLICATE
            );

            unchecked {
                ++i;
            }
        }
    }

    function isRelayUriAvailable(string memory _uri) private view returns (bool) {
        // if relay with given uri does not exist, it will throw an exception
        try mevBoostRelayAllowedList.get_relay_by_uri(_uri) returns (
            IMEVBoostRelayAllowedList.Relay memory
        ) {
            return false;
        } catch {
            return true;
        }
    }
}
