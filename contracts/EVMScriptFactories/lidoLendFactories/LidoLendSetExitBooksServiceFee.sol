// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to set the same service-fee configuration on multiple Lido Lend exit books
contract LidoLendSetExitBooksServiceFee is TrustedCaller, IEVMScriptFactory {
    string private constant ERROR_EMPTY_EXIT_BOOKS = "EMPTY_EXIT_BOOKS";
    string private constant ERROR_ZERO_EXIT_BOOK = "ZERO_EXIT_BOOK";
    string private constant ERROR_FEE_TOO_HIGH = "FEE_TOO_HIGH";
    string private constant ERROR_FEE_RECIPIENT_REQUIRED = "FEE_RECIPIENT_REQUIRED";

    uint256 private constant MAX_SERVICE_FEE = 0.25e18;

    constructor(address _trustedCaller) TrustedCaller(_trustedCaller) {}

    /// @notice Creates one `setServiceFee` call per exit book, preserving input order
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address[] exitBooks, address feeRecipient, uint256 serviceFee)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory exitBooks,
            address feeRecipient,
            uint256 serviceFee
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

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

    /// @notice Decodes call data used by createEVMScript
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            address[] memory exitBooks,
            address feeRecipient,
            uint256 serviceFee
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            address[] memory exitBooks,
            address feeRecipient,
            uint256 serviceFee
        )
    {
        return abi.decode(_evmScriptCallData, (address[], address, uint256));
    }
}
