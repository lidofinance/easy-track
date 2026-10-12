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
        SetErc4626ExitBookAllowed
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";
    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ZERO_EXIT_BOOK = "ZERO_EXIT_BOOK";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Morpho exit book targeted by market allow-list actions
    address public immutable morphoExitBook;
    /// @notice ERC-4626 exit book targeted by vault allow-list actions
    address public immutable erc4626ExitBook;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _morphoExitBook,
        address _erc4626ExitBook
    ) TrustedCaller(_trustedCaller) {
        require(_morphoExitBook != address(0), ERROR_ZERO_EXIT_BOOK);
        require(_erc4626ExitBook != address(0), ERROR_ZERO_EXIT_BOOK);
        morphoExitBook = _morphoExitBook;
        erc4626ExitBook = _erc4626ExitBook;
    }

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
        returns (MarketParams[] memory marketParamsList, bool allowed)
    {
        (marketParamsList, allowed) = abi.decode(_payload, (MarketParams[], bool));
    }

    /// @notice Decodes a SetErc4626ExitBookAllowed payload
    function decodeSetErc4626ExitBookAllowedPayload(bytes memory _payload)
        public
        pure
        returns (address[] memory vaults, bool allowed)
    {
        (vaults, allowed) = abi.decode(_payload, (address[], bool));
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
            MarketParams[] memory marketParamsList,
            bool allowed
        ) = decodeSetMorphoExitBookAllowedPayload(_payload);
        require(marketParamsList.length > 0, ERROR_EMPTY_MARKETS_LIST);

        bytes[] memory encodedCalldata = new bytes[](marketParamsList.length);
        for (uint256 i = 0; i < marketParamsList.length; ++i) {
            bytes32 marketId = keccak256(abi.encode(marketParamsList[i]));
            require(
                IMorphoExitBook(morphoExitBook).MORPHO().market(marketId).lastUpdate != 0,
                ERROR_MARKET_NOT_FOUND
            );
            encodedCalldata[i] = abi.encode(marketParamsList[i], allowed);
        }

        return
            EVMScriptCreator.createEVMScript(
                morphoExitBook,
                IMorphoExitBook.setMarketAllowed.selector,
                encodedCalldata
            );
    }

    function _createSetErc4626ExitBookAllowedEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (address[] memory vaults, bool allowed) = decodeSetErc4626ExitBookAllowedPayload(_payload);
        require(vaults.length > 0, ERROR_EMPTY_VAULTS);

        bytes[] memory encodedCalldata = new bytes[](vaults.length);
        for (uint256 i = 0; i < vaults.length; ++i) {
            require(vaults[i] != address(0), ERROR_ZERO_VAULT);
            encodedCalldata[i] = abi.encode(vaults[i], allowed);
        }

        return
            EVMScriptCreator.createEVMScript(
                erc4626ExitBook,
                IErc4626ExitBook.setVaultAllowed.selector,
                encodedCalldata
            );
    }
}
