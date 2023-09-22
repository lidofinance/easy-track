// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

import "../TrustedCaller.sol";
import "../AllowedRecipientsRegistry.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

pragma solidity ^0.8.4;

contract AddAllowedToken is TrustedCaller {
    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of AllowedRecipientsRegistry
    AllowedRecipientsRegistry public allowedRecipientsRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _allowedRecipientsRegistry) TrustedCaller(_trustedCaller) {
        allowedRecipientsRegistry = AllowedRecipientsRegistry(_allowedRecipientsRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to remove allowed recipient address from allowedRecipientsRegistry
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address recipientAddress)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        onlyTrustedCaller(_creator)
        returns (bytes memory test)
    {
        test = bytes("");
        // require(
        //     allowedRecipientsRegistry.isRecipientAllowed(_decodeEVMScriptCallData(_evmScriptCallData)),
        //     ERROR_ALLOWED_RECIPIENT_NOT_FOUND
        // );
        // return EVMScriptCreator.createEVMScript(
        //     address(allowedRecipientsRegistry), allowedRecipientsRegistry.removeRecipient.selector, _evmScriptCallData
        // );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address recipientAddress)
    /// @return recipientAddress Address to remove
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address recipientAddress)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData) private pure returns (address) {
        return abi.decode(_evmScriptCallData, (address));
    }
}