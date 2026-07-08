// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to unban a previously-banned address on one Lido Lend market
contract LidoLendUnbanGuardianSignals is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ACCOUNT_IS_NOT_BANNED = "ACCOUNT_IS_NOT_BANNED";
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

    /// @notice Creates EVMScript to unban a previously-banned address on one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address account)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address account) = _decodeEVMScriptCallData(_evmScriptCallData);

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(guardianSignals.isBanned(marketId, account), ERROR_ACCOUNT_IS_NOT_BANNED);

        return
            EVMScriptCreator.createEVMScript(
                address(guardianSignals), guardianSignals.unban.selector, abi.encode(marketId, account)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address account)
    /// @return marketId Id of the market
    /// @return account Address to unban
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, address account)
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
        returns (bytes32 marketId, address account)
    {
        (marketId, account) = abi.decode(_evmScriptCallData, (bytes32, address));
    }
}
