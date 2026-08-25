// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScripts for Lido Lend exit-book actions
contract LidoLendExitBookActions is TrustedCaller, IEVMScriptFactory {
    /// @dev Action ordinals are part of the calldata ABI. Never reorder existing members; append only.
    enum Action {
        SetMorphoExitBookAllowed,
        SetErc4626ExitBookAllowed,
        SetServiceFee
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";
    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ZERO_EXIT_BOOK = "ZERO_EXIT_BOOK";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_EMPTY_EXIT_BOOKS = "EMPTY_EXIT_BOOKS";
    string private constant ERROR_FEE_TOO_HIGH = "FEE_TOO_HIGH";
    string private constant ERROR_FEE_RECIPIENT_REQUIRED = "FEE_RECIPIENT_REQUIRED";

    // Mirrors MAX_SERVICE_FEE in lido-lend-markets/src/periphery/ExitBookBase.sol.
    uint256 private constant MAX_SERVICE_FEE = 0.25e18;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller) TrustedCaller(_trustedCaller) {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript for one exit-book action
    /// @param _creator Address who creates the EVMScript
    /// @param _evmScriptCallData Encoded envelope: abi.encode(Action action, bytes payload)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (Action action, bytes memory payload) = decodeEVMScriptCallData(_evmScriptCallData);

        if (action == Action.SetMorphoExitBookAllowed) {
            return _createSetMorphoExitBookAllowedEVMScript(payload);
        }
        if (action == Action.SetErc4626ExitBookAllowed) {
            return _createSetErc4626ExitBookAllowedEVMScript(payload);
        }
        if (action == Action.SetServiceFee) {
            return _createSetServiceFeeEVMScript(payload);
        }
        revert(ERROR_INVALID_ACTION);
    }

    // -------------
    // PUBLIC DECODERS
    // -------------

    /// @notice Decodes the outer action envelope used by createEVMScript
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (Action action, bytes memory payload)
    {
        (action, payload) = abi.decode(_evmScriptCallData, (Action, bytes));
    }

    /// @notice Decodes a SetMorphoExitBookAllowed payload
    function decodeSetMorphoExitBookAllowedPayload(bytes memory _payload)
        public
        pure
        returns (
            address exitBook,
            MarketParams[] memory marketParamsList,
            bool allowed
        )
    {
        (exitBook, marketParamsList, allowed) = abi.decode(
            _payload,
            (address, MarketParams[], bool)
        );
    }

    /// @notice Decodes a SetErc4626ExitBookAllowed payload
    function decodeSetErc4626ExitBookAllowedPayload(bytes memory _payload)
        public
        pure
        returns (
            address exitBook,
            address[] memory vaults,
            bool allowed
        )
    {
        (exitBook, vaults, allowed) = abi.decode(_payload, (address, address[], bool));
    }

    /// @notice Decodes a SetServiceFee payload
    function decodeSetServiceFeePayload(bytes memory _payload)
        public
        pure
        returns (
            address[] memory exitBooks,
            address feeRecipient,
            uint256 serviceFee
        )
    {
        (exitBooks, feeRecipient, serviceFee) = abi.decode(_payload, (address[], address, uint256));
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createSetMorphoExitBookAllowedEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (
            address exitBook,
            MarketParams[] memory marketParamsList,
            bool allowed
        ) = decodeSetMorphoExitBookAllowedPayload(_payload);
        require(exitBook != address(0), ERROR_ZERO_EXIT_BOOK);
        require(marketParamsList.length > 0, ERROR_EMPTY_MARKETS_LIST);

        bytes[] memory encodedCalldata = new bytes[](marketParamsList.length);
        for (uint256 i = 0; i < marketParamsList.length; ++i) {
            encodedCalldata[i] = abi.encode(marketParamsList[i], allowed);
        }

        return
            EVMScriptCreator.createEVMScript(
                exitBook,
                IMorphoExitBook.setMarketAllowed.selector,
                encodedCalldata
            );
    }

    function _createSetErc4626ExitBookAllowedEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (
            address exitBook,
            address[] memory vaults,
            bool allowed
        ) = decodeSetErc4626ExitBookAllowedPayload(_payload);
        require(exitBook != address(0), ERROR_ZERO_EXIT_BOOK);
        require(vaults.length > 0, ERROR_EMPTY_VAULTS);

        bytes[] memory encodedCalldata = new bytes[](vaults.length);
        for (uint256 i = 0; i < vaults.length; ++i) {
            require(vaults[i] != address(0), ERROR_ZERO_VAULT);
            encodedCalldata[i] = abi.encode(vaults[i], allowed);
        }

        return
            EVMScriptCreator.createEVMScript(
                exitBook,
                IErc4626ExitBook.setVaultAllowed.selector,
                encodedCalldata
            );
    }

    function _createSetServiceFeeEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (
            address[] memory exitBooks,
            address feeRecipient,
            uint256 serviceFee
        ) = decodeSetServiceFeePayload(_payload);

        require(exitBooks.length > 0, ERROR_EMPTY_EXIT_BOOKS);
        require(serviceFee <= MAX_SERVICE_FEE, ERROR_FEE_TOO_HIGH);
        require(feeRecipient != address(0) || serviceFee == 0, ERROR_FEE_RECIPIENT_REQUIRED);

        bytes4[] memory methodIds = new bytes4[](exitBooks.length);
        bytes[] memory callData = new bytes[](exitBooks.length);
        for (uint256 i = 0; i < exitBooks.length; ++i) {
            require(exitBooks[i] != address(0), ERROR_ZERO_EXIT_BOOK);
            methodIds[i] = IExitBook.setServiceFee.selector;
            callData[i] = abi.encode(feeRecipient, serviceFee);
        }

        return EVMScriptCreator.createEVMScript(exitBooks, methodIds, callData);
    }
}
