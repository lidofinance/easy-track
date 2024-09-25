// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../interfaces/IAllowedRecipientsRegistry.sol";
import "../interfaces/IAllowedTokensRegistry.sol";
import "../interfaces/IFinance.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IEasyTrack.sol";

/// @notice Creates EVMScript to top up allowed recipients addresses within the current spendable balance
contract TopUpAllowedRecipients is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_LENGTH_MISMATCH = "LENGTH_MISMATCH";
    string private constant ERROR_EMPTY_DATA = "EMPTY_DATA";
    string private constant ERROR_ZERO_AMOUNT = "ZERO_AMOUNT";
    string private constant ERROR_TOKEN_NOT_ALLOWED = "TOKEN_NOT_ALLOWED";
    string private constant ERROR_RECIPIENT_NOT_ALLOWED = "RECIPIENT_NOT_ALLOWED";
    string private constant ERROR_ZERO_RECIPIENT = "ZERO_RECIPIENT";
    string private constant ERROR_SUM_EXCEEDS_SPENDABLE_BALANCE = "SUM_EXCEEDS_SPENDABLE_BALANCE";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of EasyTrack contract
    IEasyTrack public immutable easyTrack;

    /// @notice Address of Aragon's Finance contract
    IFinance public immutable finance;

    /// @notice Address of AllowedRecipientsRegistry contract
    IAllowedRecipientsRegistry public immutable allowedRecipientsRegistry;

    /// @notice Address of AllowedTokensRegistry contract
    IAllowedTokensRegistry public immutable allowedTokensRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    /// @param _trustedCaller Address that has access to certain methods.
    ///     Set once on deployment and can't be changed.
    /// @param _allowedRecipientsRegistry Address of AllowedRecipientsRegistry contract
    /// @param _allowedTokensRegistry Address of AllowedTokensRegistry contract
    /// @param _finance Address of Aragon's Finance contract
    /// @param _easyTrack Address of EasyTrack contract
    constructor(
        address _trustedCaller,
        address _allowedRecipientsRegistry,
        address _allowedTokensRegistry,
        address _finance,
        address _easyTrack
    ) TrustedCaller(_trustedCaller) {
        finance = IFinance(_finance);
        allowedRecipientsRegistry = IAllowedRecipientsRegistry(_allowedRecipientsRegistry);
        allowedTokensRegistry = IAllowedTokensRegistry(_allowedTokensRegistry);
        easyTrack = IEasyTrack(_easyTrack);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to top up allowed recipients addresses
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address token, address[] recipients, uint256[] amounts) where
    /// token - address of token to top up
    /// recipients - addresses of recipients to top up
    /// amounts - corresponding amounts of token to transfer
    /// @dev note that the arrays below has one extra element to store limit enforcement calls
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address token, address[] memory recipients, uint256[] memory amounts) =
            _decodeEVMScriptCallData(_evmScriptCallData);
        uint256 normalizedAmount = _validateEVMScriptCallData(token, recipients, amounts);

        address[] memory to = new address[](recipients.length + 1);
        bytes4[] memory methodIds = new bytes4[](recipients.length + 1);
        bytes[] memory evmScriptsCalldata = new bytes[](recipients.length + 1);

        to[0] = address(allowedRecipientsRegistry);
        methodIds[0] = allowedRecipientsRegistry.updateSpentAmount.selector;
        evmScriptsCalldata[0] = abi.encode(normalizedAmount);

        for (uint256 i = 0; i < recipients.length; ++i) {
            to[i + 1] = address(finance);
            methodIds[i + 1] = finance.newImmediatePayment.selector;
            evmScriptsCalldata[i + 1] = abi.encode(token, recipients[i], amounts[i], "Easy Track: top up recipient");
        }

        return EVMScriptCreator.createEVMScript(to, methodIds, evmScriptsCalldata);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address[] recipients, uint256[] amounts) where
    /// recipients - addresses of recipients to top up
    /// amounts - corresponding amounts of token to transfer
    /// @return token Address of payout token
    /// @return recipients Addresses of recipients to top up
    /// @return amounts Amounts of token to transfer
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address token, address[] memory recipients, uint256[] memory amounts)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _validateEVMScriptCallData(address token, address[] memory _recipients, uint256[] memory _amounts)
        private
        view
        returns (uint256 normalizedAmount)
    {
        require(_amounts.length == _recipients.length, ERROR_LENGTH_MISMATCH);
        require(_recipients.length > 0, ERROR_EMPTY_DATA);
        require(allowedTokensRegistry.isTokenAllowed(token), ERROR_TOKEN_NOT_ALLOWED);

        uint256 totalAmount;

        for (uint256 i = 0; i < _recipients.length; ++i) {
            require(_amounts[i] > 0, ERROR_ZERO_AMOUNT);
            require(_recipients[i] != address(0), ERROR_ZERO_RECIPIENT);
            require(allowedRecipientsRegistry.isRecipientAllowed(_recipients[i]), ERROR_RECIPIENT_NOT_ALLOWED);
            totalAmount += _amounts[i];
        }

        normalizedAmount = allowedTokensRegistry.normalizeAmount(totalAmount, token);

        _validateSpendableBalance(normalizedAmount);
    }

    function _decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        private
        pure
        returns (address token, address[] memory recipients, uint256[] memory amounts)
    {
        return abi.decode(_evmScriptCallData, (address, address[], uint256[]));
    }

    function _validateSpendableBalance(uint256 _amount) private view {
        require(
            allowedRecipientsRegistry.isUnderSpendableBalance(_amount, easyTrack.motionDuration()),
            ERROR_SUM_EXCEEDS_SPENDABLE_BALANCE
        );
    }
}
