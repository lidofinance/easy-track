// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../ReferralPartnersRegistry.sol";
import "../interfaces/IFinance.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

/// @author psirex, dzhon
/// @notice Creates EVMScript to top up balances of referral partners
contract TopUpReferralPartners is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_LENGTH_MISMATCH = "LENGTH_MISMATCH";
    string private constant ERROR_EMPTY_DATA = "EMPTY_DATA";
    string private constant ERROR_ZERO_AMOUNT = "ZERO_AMOUNT";
    string private constant ERROR_REFERRAL_PARTNER_NOT_ALLOWED = "REFERRAL_PARTNER_NOT_ALLOWED";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of Aragon's Finance contract
    IFinance public immutable finance;

    /// @notice Address of payout token
    address public immutable payoutToken;

    /// @notice Address of referralPartnersRegistry
    ReferralPartnersRegistry public immutable referralPartnersRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _referralPartnersRegistry,
        address _finance,
        address _payoutToken
    ) TrustedCaller(_trustedCaller) {
        finance = IFinance(_finance);
        payoutToken = _payoutToken;
        referralPartnersRegistry = ReferralPartnersRegistry(_referralPartnersRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to top up balances of referral partners
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address[] _referralPartners, uint256[] _amounts) where
    /// _referralPartners - addresses of referral partners to top up
    /// _amounts - corresponding amount of tokens to transfer
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory referralPartners, uint256[] memory amounts) =
            _decodeEVMScriptCallData(_evmScriptCallData);

        _validateEVMScriptCallData(referralPartners, amounts);

        bytes[] memory evmScriptsCalldata = new bytes[](referralPartners.length);
        for (uint256 i = 0; i < referralPartners.length; ++i) {
            evmScriptsCalldata[i] = abi.encode(
                payoutToken,
                referralPartners[i],
                amounts[i],
                "Referral partner top up"
            );
        }
        return
            EVMScriptCreator.createEVMScript(
                address(finance),
                finance.newImmediatePayment.selector,
                evmScriptsCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address[] _referralPartners, uint256[] _amounts) where
    /// _referralPartners - addresses of referral partners to top up
    /// _amounts - corresponding amount of tokens to transfer
    /// @return _referralPartners Addresses of referral partners to top up
    /// @return _amounts Amounts of tokens to transfer
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address[] memory _referralPartners, uint256[] memory _amounts)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _validateEVMScriptCallData(address[] memory _referralPartners, uint256[] memory _amounts)
        private
        view
    {
        require(_referralPartners.length == _amounts.length, ERROR_LENGTH_MISMATCH);
        require(_referralPartners.length > 0, ERROR_EMPTY_DATA);
        for (uint256 i = 0; i < _referralPartners.length; ++i) {
            require(_amounts[i] > 0, ERROR_ZERO_AMOUNT);
            require(
                referralPartnersRegistry.isReferralPartner(_referralPartners[i]),
                ERROR_REFERRAL_PARTNER_NOT_ALLOWED
            );
        }
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory _referralPartners, uint256[] memory _amounts)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[]));
    }
}
