// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to update the IRM curve params of one Lido Lend market
/// @dev The call target is the configured AdaptiveCurveIrm singleton. The market id selects only the
///      market params encoded in calldata, so one fixed EasyTrack permission serves every domain market.
contract LidoLendSetIrmCurveParams is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";
    string private constant ERROR_IRM_NOT_ROUTER = "IRM_NOT_ROUTER";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLend core (resolves a market's params by id)
    ILidoLend public immutable lidoLend;
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
        lidoLend = ILidoLend(_lidoLend);
        irmRouter = _irmRouter;
        adaptiveCurveIrm = _adaptiveCurveIrm;
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
        (bytes32 marketId, AdaptiveCurveParams memory curveParams) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        MarketParams memory marketParams = lidoLend.idToMarketParams(marketId);
        require(marketParams.irm != address(0), ERROR_MARKET_NOT_FOUND);
        require(marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);

        return
            EVMScriptCreator.createEVMScript(
                adaptiveCurveIrm,
                IAdaptiveCurveIrm.setMarketCurveParams.selector,
                abi.encode(marketParams, curveParams)
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
