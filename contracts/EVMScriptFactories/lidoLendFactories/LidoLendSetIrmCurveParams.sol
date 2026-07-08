// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to update the IRM curve params of one Lido Lend market
contract LidoLendSetIrmCurveParams is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ADJUSTMENT_SPEED = "INVALID_ADJUSTMENT_SPEED";
    string private constant ERROR_INVALID_TARGET_UTILIZATION = "INVALID_TARGET_UTILIZATION";
    string private constant ERROR_INVALID_RATE_BOUNDS = "INVALID_RATE_BOUNDS";
    string private constant ERROR_INVALID_INITIAL_RATE = "INVALID_INITIAL_RATE";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";
    string private constant ERROR_CURVE_NOT_FOUND = "CURVE_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLend core (resolves a market's params by id)
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

    /// @notice Creates EVMScript to update the IRM curve params of one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, AdaptiveCurveParams curveParams)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, AdaptiveCurveParams memory curveParams) =
            _decodeEVMScriptCallData(_evmScriptCallData);
        require(curveParams.adjustmentSpeed >= 0, ERROR_INVALID_ADJUSTMENT_SPEED);
        require(curveParams.targetUtilization > 0, ERROR_INVALID_TARGET_UTILIZATION);
        require(
            curveParams.minRateAtTarget > 0 && curveParams.maxRateAtTarget >= curveParams.minRateAtTarget,
            ERROR_INVALID_RATE_BOUNDS
        );
        require(
            curveParams.initialRateAtTarget >= curveParams.minRateAtTarget
                && curveParams.initialRateAtTarget <= curveParams.maxRateAtTarget,
            ERROR_INVALID_INITIAL_RATE
        );

        MarketParams memory marketParams = lidoLend.idToMarketParams(marketId);
        require(marketParams.irm != address(0), ERROR_MARKET_NOT_FOUND);
        address curve = IIrmRouter(marketParams.irm).marketIrm(marketId);
        require(curve != address(0), ERROR_CURVE_NOT_FOUND);

        return
            EVMScriptCreator.createEVMScript(
                curve, IAdaptiveCurveIrm.setMarketCurveParams.selector, abi.encode(marketParams, curveParams)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, AdaptiveCurveParams curveParams)
    /// @return marketId Id of the market
    /// @return curveParams Decoded curve params
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, AdaptiveCurveParams memory curveParams)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, AdaptiveCurveParams memory curveParams)
    {
        (marketId, curveParams) = abi.decode(_evmScriptCallData, (bytes32, AdaptiveCurveParams));
    }
}
