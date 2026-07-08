// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to grant instant collateral activation to one caller on one Lido Lend market
contract LidoLendGrantInstantActivation is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_CALLER = "ZERO_CALLER";
    string private constant ERROR_INSTANT_ACTIVATION_ALREADY_GRANTED = "INSTANT_ACTIVATION_ALREADY_GRANTED";
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

    /// @notice Creates EVMScript to grant instant collateral activation to one caller on one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address caller)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address caller) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(caller != address(0), ERROR_ZERO_CALLER);

        ILidoLendMarketController marketController = _controllerOf(marketId);
        require(!marketController.hasInstantActivation(caller), ERROR_INSTANT_ACTIVATION_ALREADY_GRANTED);

        return
            EVMScriptCreator.createEVMScript(
                address(marketController), marketController.grantInstantActivation.selector, abi.encode(caller)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address caller)
    /// @return marketId Id of the market
    /// @return caller Caller to grant instant activation
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, address caller)
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
        returns (bytes32 marketId, address caller)
    {
        (marketId, caller) = abi.decode(_evmScriptCallData, (bytes32, address));
    }
}
