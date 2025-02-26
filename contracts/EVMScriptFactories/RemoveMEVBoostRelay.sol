// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMEVBoostRelayAllowedList.sol";

/// @author katamarinaki
/// @notice Creates EVMScript to add new MEV boost relay to MEV Boost relay allow list
contract RemoveMEVBoostRelay is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";
    string private constant ERROR_RELAYS_COUNT_MISMATCH = "RELAYS_COUNT_MISMATCH";
    string private constant ERROR_EMPTY_RELAY_URI = "EMPTY_RELAY_URI";
    string private constant ERROR_NO_RELAY_WITH_GIVEN_URI = "NO_RELAY_WITH_GIVEN_URI";

    // -------------
    // CONSTANTS
    // -------------

    /// @notice selector for the remove_relay method in the MEVBoostRelayAllowedList
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

    /// @notice Creates EVMScript to add new MEV boost relay to MEV Boost relay allow list
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded relay URIs: string[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        string[] memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        uint256 calldataLength = decodedCallData.length;

        // validate that the call data is not empty and that the relays count does not exceed the allowed list
        require(calldataLength > 0, ERROR_EMPTY_CALLDATA);
        require(
            mevBoostRelayAllowedList.get_relays_amount() >= calldataLength,
            ERROR_RELAYS_COUNT_MISMATCH
        );

        bytes4[] memory methodIds = new bytes4[](calldataLength);
        bytes[] memory encodedCalldata = new bytes[](calldataLength);

        for (uint256 i; i < calldataLength; ) {
            _validateRelayURI(decodedCallData[i]);

            methodIds[i] = REMOVE_RELAY_SELECTOR;
            encodedCalldata[i] = abi.encode(decodedCallData[i]);

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
    /// @param _evmScriptCallData Encoded relay URIs: string[]
    /// @return relayUris string[]
    function decodeEVMScriptCallData(
        bytes calldata _evmScriptCallData
    ) external pure returns (string[] memory relayUris) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (string[] memory relayUris) {
        (relayUris) = abi.decode(_evmScriptCallData, (string[]));
    }

    function _validateRelayURI(string memory _relayURI) private view {
        require(bytes(_relayURI).length > 0, ERROR_EMPTY_RELAY_URI);
        require(_relayURIExists(_relayURI), ERROR_NO_RELAY_WITH_GIVEN_URI);
    }

    function _relayURIExists(string memory _uri) private view returns (bool) {
        // if relay with given uri does not exist, it will throw an exception
        try mevBoostRelayAllowedList.get_relay_by_uri(_uri) returns (
            IMEVBoostRelayAllowedList.Relay memory
        ) {
            return true;
        } catch {
            return false;
        }
    }
}
