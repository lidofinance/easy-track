// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to set instant collateral activation for one caller on one Lido Lend market
contract LidoLendSetInstantActivation is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_CALLER = "ZERO_CALLER";
    string private constant ERROR_SAME_INSTANT_ACTIVATION_STATUS = "SAME_INSTANT_ACTIVATION_STATUS";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set instant collateral activation for one caller on one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address caller, bool enabled)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address caller, bool enabled) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        require(caller != address(0), ERROR_ZERO_CALLER);

        ILidoLendMarketController marketController = _controllerOf(marketId);
        require(
            marketController.hasInstantActivation(caller) != enabled,
            ERROR_SAME_INSTANT_ACTIVATION_STATUS
        );

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setInstantActivation.selector,
                abi.encode(marketId, caller, enabled)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address caller, bool enabled)
    /// @return marketId Id of the market
    /// @return caller Caller whose instant activation status is set
    /// @return enabled Target instant activation status
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            bytes32 marketId,
            address caller,
            bool enabled
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
            bytes32 marketId,
            address caller,
            bool enabled
        )
    {
        (marketId, caller, enabled) = abi.decode(_evmScriptCallData, (bytes32, address, bool));
    }
}
