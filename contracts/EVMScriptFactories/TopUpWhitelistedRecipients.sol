// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../WhitelistedRecipientsRegistry.sol";
import "../interfaces/IFinance.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

/// @notice Creates EVMScript to check limits and top up whitelisted recipients addresses
contract TopUpWhitelistedRecipients is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_LENGTH_MISMATCH = "LENGTH_MISMATCH";
    string private constant ERROR_EMPTY_DATA = "EMPTY_DATA";
    string private constant ERROR_ZERO_AMOUNT = "ZERO_AMOUNT";
    string private constant ERROR_WHITELISTED_RECEPIENT_NOT_FOUND =
        "ERROR_WHITELISTED_RECEPIENT_NOT_FOUND";
    string private constant ERROR_SUM_EXCEEDS_LIMIT = "SUM_EXCEEDS_LIMIT";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of Aragon's Finance contract
    IFinance public immutable finance;

    /// @notice Address of payout token
    address public immutable token;

    /// @notice Address of WhitelistedRecipientsRegistry
    WhitelistedRecipientsRegistry public immutable whitelistedRecipientsRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _whitelistedRecipientsRegistry,
        address _finance,
        address _token
    ) TrustedCaller(_trustedCaller) {
        finance = IFinance(_finance);
        token = _token;
        whitelistedRecipientsRegistry = WhitelistedRecipientsRegistry(
            _whitelistedRecipientsRegistry
        );
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to top up whitelisted recipients addressees
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address[] _whitelistedRecipients, uint256[] _amounts) where
    /// _whitelistedRecipients - addresses of whitelisted recipients to top up
    /// _amounts - corresponding amount of tokens to transfer
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory whitelistedRecipients,
            uint256[] memory amounts
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        _validateEVMScriptCallData(whitelistedRecipients, amounts);

        bytes[] memory evmScriptsCalldata = new bytes[](whitelistedRecipients.length);
        uint256 sum = 0;
        for (uint256 i = 0; i < whitelistedRecipients.length; ++i) {
            evmScriptsCalldata[i] = abi.encode(
                token,
                whitelistedRecipients[i],
                amounts[i],
                "Top up whitelisted recipients"
            );
            sum += amounts[i];
        }

        _checkLimit(sum);

        bytes memory _evmScript_checkAndUpdateLimits = EVMScriptCreator.createEVMScript(
            address(whitelistedRecipientsRegistry),
            whitelistedRecipientsRegistry.checkAndUpdateLimits.selector,
            abi.encode(sum)
        );

        bytes memory _evmScript_newImmediatePayment = EVMScriptCreator.createEVMScript(
            address(finance),
            finance.newImmediatePayment.selector,
            evmScriptsCalldata
        );

        return
            EVMScriptCreator.concatScripts(
                _evmScript_checkAndUpdateLimits,
                _evmScript_newImmediatePayment
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address[] _whitelistedRecipients, uint256[] _amounts) where
    /// _whitelistedRecipients - addresses of whitelisted recipients to top up
    /// _amounts - corresponding amount of tokens to transfer
    /// @return _whitelistedRecipients Addresses of whitelisted recipients to top up
    /// @return _amounts Amounts of tokens to transfer
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address[] memory _whitelistedRecipients, uint256[] memory _amounts)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _validateEVMScriptCallData(
        address[] memory _whitelistedRecipients,
        uint256[] memory _amounts
    ) private view {
        require(_amounts.length == _whitelistedRecipients.length, ERROR_LENGTH_MISMATCH);
        require(_whitelistedRecipients.length > 0, ERROR_EMPTY_DATA);
        for (uint256 i = 0; i < _whitelistedRecipients.length; ++i) {
            require(_amounts[i] > 0, ERROR_ZERO_AMOUNT);
            require(
                whitelistedRecipientsRegistry.isWhitelistedRecipient(_whitelistedRecipients[i]),
                ERROR_WHITELISTED_RECEPIENT_NOT_FOUND
            );
        }
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory _whitelistedRecipients, uint256[] memory _amounts)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[]));
    }

    function _checkLimit(uint256 _sum) private view {
        require(whitelistedRecipientsRegistry.isUnderLimit(_sum), ERROR_SUM_EXCEEDS_LIMIT);
    }
}
