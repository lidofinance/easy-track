// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to re-route one Lido Lend market to a different IRM model on the shared router
/// @dev The call target is the configured IrmRouter singleton. The market id selects only the market params
///      encoded in calldata, so one fixed EasyTrack permission serves every domain market.
contract LidoLendSetMarketIrm is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_IRM = "ZERO_IRM";
    string private constant ERROR_IRM_NOT_CONTRACT = "IRM_NOT_CONTRACT";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";
    string private constant ERROR_IRM_NOT_ROUTER = "IRM_NOT_ROUTER";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLend core (resolves a market's params by id)
    ILidoLend public immutable lidoLend;
    /// @notice Address of the domain's IrmRouter committed to every supported market id
    address public immutable irmRouter;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _lidoLend,
        address _irmRouter
    ) TrustedCaller(_trustedCaller) {
        lidoLend = ILidoLend(_lidoLend);
        irmRouter = _irmRouter;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to re-route this market to a different IRM model
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address irm)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address newIrm) = _decodeEVMScriptCallData(_evmScriptCallData);
        require(newIrm != address(0), ERROR_ZERO_IRM);
        require(newIrm.code.length > 0, ERROR_IRM_NOT_CONTRACT);

        MarketParams memory marketParams = lidoLend.idToMarketParams(marketId);
        require(marketParams.irm != address(0), ERROR_MARKET_NOT_FOUND);
        require(marketParams.irm == irmRouter, ERROR_IRM_NOT_ROUTER);

        return
            EVMScriptCreator.createEVMScript(
                irmRouter,
                IIrmRouter.setMarketIrm.selector,
                abi.encode(marketParams, newIrm)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address irm)
    /// @return marketId Id of the market to re-route
    /// @return irm New IRM model to route the market to
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, address irm)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, address irm)
    {
        (marketId, irm) = abi.decode(_evmScriptCallData, (bytes32, address));
    }
}
