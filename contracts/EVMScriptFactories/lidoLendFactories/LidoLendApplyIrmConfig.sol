// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendFactoryBase.sol";

/// @notice Creates an EVMScript to apply an Adaptive Curve IRM config to a Lido Lend market
contract LidoLendApplyIrmConfig is LidoLendFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_IRM_CONFIG = "ZERO_IRM_CONFIG";
    string private constant ERROR_IRM_NOT_ROUTER = "IRM_NOT_ROUTER";
    string private constant ERROR_MARKET_PAUSED = "MARKET_PAUSED";

    // -------------
    // VARIABLES
    // -------------

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
    ) LidoLendFactoryBase(_trustedCaller, _lidoLend) {
        irmRouter = _irmRouter;
        adaptiveCurveIrm = _adaptiveCurveIrm;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript that accrues interest before applying a new IRM config
    /// @param _creator Address who creates the EVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address irmConfig)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address irmConfig) = decodeEVMScriptCallData(_evmScriptCallData);
        require(irmConfig != address(0), ERROR_ZERO_IRM_CONFIG);

        MarketParams memory marketParams = ILidoLend(lidoLend).idToMarketParams(marketId);
        require(marketParams.irm != address(0), ERROR_MARKET_NOT_FOUND);
        require(marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);
        ILidoLendMarketController marketController = _marketController(marketId);
        require(
            address(marketController) == address(0) || !marketController.isPaused(),
            ERROR_MARKET_PAUSED
        );

        address[] memory to = new address[](2);
        bytes4[] memory methodIds = new bytes4[](2);
        bytes[] memory callData = new bytes[](2);

        to[0] = lidoLend;
        methodIds[0] = ILidoLend.accrueInterest.selector;
        callData[0] = abi.encode(marketParams);

        to[1] = adaptiveCurveIrm;
        methodIds[1] = IConfigurableIrm.applyIrmConfig.selector;
        callData[1] = abi.encode(marketParams, irmConfig);

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    /// @notice Decodes call data used by createEVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address irmConfig)
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (bytes32 marketId, address irmConfig)
    {
        return abi.decode(_evmScriptCallData, (bytes32, address));
    }
}
