// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to raise the supply cap of one Lido Lend market
contract LidoLendSetSupplyCap is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_CAP_NOT_HIGHER = "CAP_NOT_HIGHER";
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

    /// @notice Creates EVMScript to raise the supply cap of one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 cap)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newCap) = _decodeEVMScriptCallData(_evmScriptCallData);

        ILidoLendMarketController marketController = _controllerOf(marketId);
        require(newCap != 0 && newCap > marketController.supplyCap(), ERROR_CAP_NOT_HIGHER);

        return
            EVMScriptCreator.createEVMScript(
                address(marketController), marketController.setSupplyCap.selector, abi.encode(newCap)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 cap)
    /// @return marketId Id of the market
    /// @return cap New supply cap
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, uint256 cap)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _controllerOf(bytes32 marketId) private view returns (ILidoLendMarketController) {
        address controller = lidoLend.marketController(marketId);
        require(controller != address(0), ERROR_MARKET_NOT_FOUND);
        return ILidoLendMarketController(controller);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, uint256 cap)
    {
        (marketId, cap) = abi.decode(_evmScriptCallData, (bytes32, uint256));
    }
}
