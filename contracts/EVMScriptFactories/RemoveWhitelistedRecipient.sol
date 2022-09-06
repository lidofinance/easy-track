// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../WhitelistedRecipientsRegistry.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

/// @author psirex, zuzueeka
/// @notice Creates EVMScript to remove whitelisted recipient address from whitelistedRecipientsRegistry
contract RemoveWhitelistedRecipient is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_WHITELISTED_RECIPIENT_NOT_FOUND =
        "WHITELISTED_RECIPIENT_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of WhitelistedRecipientsRegistry
    WhitelistedRecipientsRegistry public immutable whitelistedRecipientsRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _whitelistedRecipientsRegistry)
        TrustedCaller(_trustedCaller)
    {
        whitelistedRecipientsRegistry = WhitelistedRecipientsRegistry(
            _whitelistedRecipientsRegistry
        );
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to remove whitelisted recipient address from whitelistedRecipientsRegistry
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address _recipientAddress)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        require(
            whitelistedRecipientsRegistry.isWhitelistedRecipient(
                _decodeEVMScriptCallData(_evmScriptCallData)
            ),
            ERROR_WHITELISTED_RECIPIENT_NOT_FOUND
        );
        return
            EVMScriptCreator.createEVMScript(
                address(whitelistedRecipientsRegistry),
                whitelistedRecipientsRegistry.removeWhitelistedRecipient.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address _recipientAddress)
    /// @return _recipientAddress Address to remove
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address _recipientAddress)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address)
    {
        return abi.decode(_evmScriptCallData, (address));
    }
}
