// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to set a Lido Lend market's allow-list state on the domain's two exit books
contract LidoLendSetMarketExitBookAllowed is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_VAULT_MARKET_MISMATCH = "VAULT_MARKET_MISMATCH";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the domain's MorphoExitBook (over lenders' core supply positions)
    address public immutable morphoExitBook;
    /// @notice Address of the domain's Erc4626ExitBook (over lenders' vault shares)
    address public immutable erc4626ExitBook;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _morphoExitBook,
        address _erc4626ExitBook
    ) TrustedCaller(_trustedCaller) {
        morphoExitBook = _morphoExitBook;
        erc4626ExitBook = _erc4626ExitBook;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set a market's allow-list state on the domain's two exit books
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (MarketParams marketParams, address vault, bool allowed)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (MarketParams memory marketParams, address vault, bool allowed) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        require(vault != address(0), ERROR_ZERO_VAULT);
        require(
            ILidoLendVault(vault).marketId() == keccak256(abi.encode(marketParams)),
            ERROR_VAULT_MARKET_MISMATCH
        );

        address[] memory to = new address[](2);
        to[0] = morphoExitBook;
        to[1] = erc4626ExitBook;

        bytes4[] memory methodIds = new bytes4[](2);
        methodIds[0] = IMorphoExitBook.setMarketAllowed.selector;
        methodIds[1] = IErc4626ExitBook.setVaultAllowed.selector;

        bytes[] memory callData = new bytes[](2);
        callData[0] = abi.encode(marketParams, allowed);
        callData[1] = abi.encode(vault, allowed);

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (MarketParams marketParams, address vault, bool allowed)
    /// @return marketParams Market params (identifies the market on the Morpho book)
    /// @return vault The market's ERC-4626 vault (identifies it on the ERC-4626 book)
    /// @return allowed Target allow-list state to set on both books
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            MarketParams memory marketParams,
            address vault,
            bool allowed
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            MarketParams memory marketParams,
            address vault,
            bool allowed
        )
    {
        (marketParams, vault, allowed) = abi.decode(
            _evmScriptCallData,
            (MarketParams, address, bool)
        );
    }
}
