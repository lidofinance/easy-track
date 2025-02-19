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

    // -------------
    // CONSTANTS
    // -------------

    uint256 private constant MAX_NUM_RELAYS = 40;
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
    /// @param _evmScriptCallData Encoded: Relay[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        (
            uint256 relaysCount,
            AddMEVBoostRelayInput[] memory decodedCallData
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        address[] memory toAddresses = new address[](decodedCallData.length);
        bytes4[] memory methodIds = new bytes4[](decodedCallData.length);
        bytes[] memory encodedCalldata = new bytes[](decodedCallData.length);

        _validateInputData(relaysCount, decodedCallData);

        for (uint256 i = 0; i < decodedCallData.length; ++i) {
            toAddresses[i] = address(mevBoostRelayAllowedList);
            methodIds[i] = ADD_RELAY_SELECTOR;
            encodedCalldata[i] = abi.encode(
                decodedCallData[i].uri,
                decodedCallData[i].operator,
                decodedCallData[i].is_mandatory,
                decodedCallData[i].description
            );
        }

        return EVMScriptCreator.createEVMScript(toAddresses, methodIds, encodedCalldata);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (uint256, AddMEVBoostRelayInput[])
    /// @return relaysCount current number of relays in allowed list
    /// @return relays AddMEVBoostRelayInput[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
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

    function _validateInputData(
        uint256 _relaysCount,
        AddMEVBoostRelayInput[] memory _relayInputs
    ) private view {
        uint256 calldataLength = _relayInputs.length;

        require(calldataLength > 0, ERROR_EMPTY_CALLDATA);

        require(
            mevBoostRelayAllowedList.get_relays_amount() == _relaysCount,
            ERROR_RELAYS_COUNT_MISMATCH
        );

        require(_relaysCount + calldataLength <= MAX_NUM_RELAYS, ERROR_MAX_NUM_RELAYS_EXCEEDED);

        for (uint256 i = 0; i < calldataLength; ++i) {
            string memory uri = _relayInputs[i].uri;
            require(bytes(uri).length > 0, ERROR_EMPTY_RELAY_URI);

            require(isRelayUriAvailable(uri), ERROR_RELAY_URI_ALREADY_EXISTS);
        }
    }

    function isRelayUriAvailable(string memory uri) private view returns (bool) {
        try mevBoostRelayAllowedList.get_relay_by_uri(uri) returns (
            IMEVBoostRelayAllowedList.Relay memory
        ) {
            return false;
        } catch {
            return true;
        }
    }
}
