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
    /// @param _evmScriptCallData Encoded: Relay[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        string[] memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        uint256 decodedCallDataLength = decodedCallData.length;

        bytes4[] memory methodIds = new bytes4[](decodedCallDataLength);
        bytes[] memory encodedCalldata = new bytes[](decodedCallDataLength);

        _validateInputData(decodedCallData);

        for (uint256 i; i < decodedCallDataLength; ) {
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
    /// @param _evmScriptCallData Encoded (uint256, AddMEVBoostRelayInput[])
    /// @return relayUris string[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
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

    function _validateInputData(string[] memory _relayUris) private view {
        uint256 calldataLength = _relayUris.length;
        require(calldataLength > 0, ERROR_EMPTY_CALLDATA);

        require(
            mevBoostRelayAllowedList.get_relays_amount() >= calldataLength,
            ERROR_RELAYS_COUNT_MISMATCH
        );

        for (uint256 i; i < calldataLength; ) {
            string memory uri = _relayUris[i];
            require(bytes(uri).length > 0, ERROR_EMPTY_RELAY_URI);

            require(isRelayUriPresented(uri), ERROR_NO_RELAY_WITH_GIVEN_URI);

            unchecked {
                ++i;
            }
        }
    }

    function isRelayUriPresented(string memory uri) private view returns (bool) {
        try mevBoostRelayAllowedList.get_relay_by_uri(uri) returns (
            IMEVBoostRelayAllowedList.Relay memory
        ) {
            return true;
        } catch {
            return false;
        }
    }
}
