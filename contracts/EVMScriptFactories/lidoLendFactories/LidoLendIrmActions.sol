// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScripts for IRM-management actions on Lido Lend markets
contract LidoLendIrmActions is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";
    string private constant ERROR_ZERO_IRM = "ZERO_IRM";
    string private constant ERROR_ZERO_IRM_CONFIG = "ZERO_IRM_CONFIG";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";
    string private constant ERROR_IRM_NOT_ROUTER = "IRM_NOT_ROUTER";

    // -------------
    // TYPES
    // -------------

    /// @dev Action ordinals are part of the calldata ABI. Never reorder existing members; append only.
    enum Action {
        SetIrmConfig,
        SetMarketIrm
    }

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLend core (resolves a market's params by id)
    address public immutable lidoLend;
    /// @notice Address of the domain's IrmRouter committed to every supported market id
    address public immutable irmRouter;
    /// @notice Address of the domain's AdaptiveCurveIrm singleton
    address public immutable adaptiveCurveIrm;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _lidoLend,
        address _irmRouter,
        address _adaptiveCurveIrm
    ) TrustedCaller(_trustedCaller) {
        lidoLend = _lidoLend;
        irmRouter = _irmRouter;
        adaptiveCurveIrm = _adaptiveCurveIrm;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript for exactly one IRM-management action
    /// @param _creator Address who creates the EVMScript
    /// @param _evmScriptCallData Encoded tuple: (Action action, bytes payload)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (Action action, bytes memory payload) = decodeEVMScriptCallData(_evmScriptCallData);

        if (action == Action.SetIrmConfig) {
            return _createSetIrmConfigEVMScript(payload);
        }
        if (action == Action.SetMarketIrm) {
            return _createSetMarketIrmEVMScript(payload);
        }

        revert(ERROR_INVALID_ACTION);
    }

    // ------------------
    // PUBLIC DECODERS
    // ------------------

    /// @notice Decodes the common IRM-action envelope
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (Action action, bytes memory payload)
    {
        (action, payload) = abi.decode(_evmScriptCallData, (Action, bytes));
    }

    /// @notice Decodes SetIrmConfig payload: (bytes32 marketId, address irmConfig)
    function decodeSetIrmConfigPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, address irmConfig)
    {
        (marketId, irmConfig) = abi.decode(_payload, (bytes32, address));
    }

    /// @notice Decodes SetMarketIrm payload: (bytes32 marketId, address newIrm)
    function decodeSetMarketIrmPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, address newIrm)
    {
        (marketId, newIrm) = abi.decode(_payload, (bytes32, address));
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createSetIrmConfigEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address irmConfig) = decodeSetIrmConfigPayload(_payload);
        require(irmConfig != address(0), ERROR_ZERO_IRM_CONFIG);

        MarketParams memory marketParams = ILidoLend(lidoLend).idToMarketParams(marketId);
        require(marketParams.irm != address(0), ERROR_MARKET_NOT_FOUND);
        require(marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);

        return
            EVMScriptCreator.createEVMScript(
                adaptiveCurveIrm,
                IConfigurableIrm.applyIrmConfig.selector,
                abi.encode(marketParams, irmConfig)
            );
    }

    function _createSetMarketIrmEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address newIrm) = decodeSetMarketIrmPayload(_payload);
        require(newIrm != address(0), ERROR_ZERO_IRM);

        MarketParams memory marketParams = ILidoLend(lidoLend).idToMarketParams(marketId);
        require(marketParams.irm != address(0), ERROR_MARKET_NOT_FOUND);
        require(marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);

        return
            EVMScriptCreator.createEVMScript(
                irmRouter,
                IIrmRouter.setMarketIrm.selector,
                abi.encode(marketParams, newIrm)
            );
    }
}
