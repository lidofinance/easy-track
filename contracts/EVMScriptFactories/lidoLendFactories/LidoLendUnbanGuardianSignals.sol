// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to unban a previously-banned address on one or more Lido Lend markets
contract LidoLendUnbanGuardianSignals is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ACCOUNT_IS_NOT_BANNED = "ACCOUNT_IS_NOT_BANNED";
    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLend core (resolves a market's controller by id)
    ILidoLend public immutable lidoLend;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLend) TrustedCaller(_trustedCaller) {
        lidoLend = ILidoLend(_lidoLend);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to unban a previously-banned address on one or more Lido Lend markets
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32[] marketIds, address account)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32[] memory marketIds, address account) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(marketIds.length > 0, ERROR_EMPTY_MARKETS_LIST);

        address[] memory targets = new address[](marketIds.length);
        bytes4[] memory selectors = new bytes4[](marketIds.length);
        bytes[] memory calldatas = new bytes[](marketIds.length);

        for (uint256 i = 0; i < marketIds.length; ++i) {
            bytes32 marketId = marketIds[i];
            IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
            require(guardianSignals.isBanned(marketId, account), ERROR_ACCOUNT_IS_NOT_BANNED);

            targets[i] = address(guardianSignals);
            selectors[i] = guardianSignals.unban.selector;
            calldatas[i] = abi.encode(marketId, account);
        }

        return EVMScriptCreator.createEVMScript(targets, selectors, calldatas);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (bytes32[] marketIds, address account)
    /// @return marketIds Ids of the markets
    /// @return account Address to unban
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32[] memory marketIds, address account)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _guardianSignalsOf(bytes32 marketId) private view returns (IGuardianSignals) {
        address controller = lidoLend.marketController(marketId);
        require(controller != address(0), ERROR_MARKET_NOT_FOUND);
        return IGuardianSignals(ILidoLendMarketController(controller).guardianSignals());
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32[] memory marketIds, address account)
    {
        (marketIds, account) = abi.decode(_evmScriptCallData, (bytes32[], address));
    }
}
