// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to remove a risk steward from one Lido Lend market
contract LidoLendRemoveRiskSteward is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_STEWARD_NOT_FOUND = "STEWARD_NOT_FOUND";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the RiskStewardDashboard
    address public immutable riskStewardDashboard;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _riskStewardDashboard)
        TrustedCaller(_trustedCaller)
    {
        riskStewardDashboard = _riskStewardDashboard;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to remove a risk steward from one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address steward)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address steward) = _decodeEVMScriptCallData(_evmScriptCallData);
        IRiskStewardDashboard dashboard = IRiskStewardDashboard(riskStewardDashboard);
        ILidoLend core = dashboard.LIDO_LEND();
        require(core.marketController(marketId) != address(0), ERROR_MARKET_NOT_FOUND);
        require(dashboard.isMarketSteward(marketId, steward), ERROR_STEWARD_NOT_FOUND);

        return
            EVMScriptCreator.createEVMScript(
                riskStewardDashboard,
                dashboard.removeMarketSteward.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address steward)
    /// @return marketId Id of the market
    /// @return steward Steward address to remove
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, address steward)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, address steward)
    {
        (marketId, steward) = abi.decode(_evmScriptCallData, (bytes32, address));
    }
}
