// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../ReferralPartnersRegistry.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

/// @author psirex, dzhon
/// @notice Creates EVMScript to add new referral partner address to ReferralPartnersRegistry
contract AddReferralPartner is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_REFERRAL_PARTNER_ALREADY_ADDED = "REFERRAL_PARTNER_ALREADY_ADDED";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of ReferralPartnersRegistry
    ReferralPartnersRegistry public immutable referralPartnersRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _referralPartnersRegistry)
        TrustedCaller(_trustedCaller)
    {
        referralPartnersRegistry = ReferralPartnersRegistry(_referralPartnersRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to add new referral partner address to ReferralPartnersRegistry
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address _referralPartner)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address referralPartnerAddress, ) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(
            !referralPartnersRegistry.isReferralPartner(referralPartnerAddress),
            ERROR_REFERRAL_PARTNER_ALREADY_ADDED
        );

        return
            EVMScriptCreator.createEVMScript(
                address(referralPartnersRegistry),
                referralPartnersRegistry.addReferralPartner.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address _referralPartner, string _title)
    /// @return _referralPartner Address of new referral partner
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address, string memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address, string memory)
    {
        return abi.decode(_evmScriptCallData, (address, string));
    }
}
