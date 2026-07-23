// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to update the collateral-activation config of one Lido Lend market
contract LidoLendSetCollateralActivationConfig is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_SAME_CONFIG = "SAME_CONFIG";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLendOwner facade
    ILidoLendOwner public immutable lidoLendOwner;
    /// @notice Address of the LidoLend core (resolves a market's controller by id, for validation)
    ILidoLend public immutable lidoLend;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner) TrustedCaller(_trustedCaller) {
        lidoLendOwner = ILidoLendOwner(_lidoLendOwner);
        lidoLend = ILidoLendOwner(_lidoLendOwner).LIDO_LEND();
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to update the collateral-activation config of one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, CollateralActivationConfig cfg)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            bytes32 marketId,
            ILidoLendMarketController.CollateralActivationConfig memory newCfg
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        ILidoLendMarketController marketController = _controllerOf(marketId);
        require(
            keccak256(abi.encode(newCfg)) !=
                keccak256(abi.encode(marketController.collateralActivationConfig())),
            ERROR_SAME_CONFIG
        );

        return
            EVMScriptCreator.createEVMScript(
                address(lidoLendOwner),
                lidoLendOwner.setMarketCollateralActivationConfig.selector,
                abi.encode(marketId, newCfg)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, CollateralActivationConfig cfg)
    /// @return marketId Id of the market
    /// @return cfg Decoded collateral-activation config
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, ILidoLendMarketController.CollateralActivationConfig memory cfg)
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
        returns (bytes32 marketId, ILidoLendMarketController.CollateralActivationConfig memory cfg)
    {
        (marketId, cfg) = abi.decode(
            _evmScriptCallData,
            (bytes32, ILidoLendMarketController.CollateralActivationConfig)
        );
    }
}
