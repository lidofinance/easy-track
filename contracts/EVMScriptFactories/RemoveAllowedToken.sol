// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

import "../TrustedCaller.sol";
import "../AllowedRecipientsRegistry.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

pragma solidity ^0.8.4;

contract RemoveAllowedToken is TrustedCaller {
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
