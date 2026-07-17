// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to add a risk steward to one Lido Lend market
contract LidoLendAddRiskSteward is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_STEWARD = "ZERO_STEWARD";
    string private constant ERROR_STEWARD_ALREADY_ADDED = "STEWARD_ALREADY_ADDED";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLend core (validates the market exists by id)
    ILidoLend public immutable lidoLend;
    /// @notice Address of the RiskStewardDashboard
    IRiskStewardDashboard public immutable riskStewardDashboard;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLend, address _riskStewardDashboard)
        TrustedCaller(_trustedCaller)
    {
        lidoLend = ILidoLend(_lidoLend);
        riskStewardDashboard = IRiskStewardDashboard(_riskStewardDashboard);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to add a risk steward to one Lido Lend market
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
        require(steward != address(0), ERROR_ZERO_STEWARD);
        require(lidoLend.marketController(marketId) != address(0), ERROR_MARKET_NOT_FOUND);
        require(!riskStewardDashboard.isMarketSteward(marketId, steward), ERROR_STEWARD_ALREADY_ADDED);

        return
            EVMScriptCreator.createEVMScript(
                address(riskStewardDashboard), riskStewardDashboard.addMarketSteward.selector, _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address steward)
    /// @return marketId Id of the market
    /// @return steward Steward address to add
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
