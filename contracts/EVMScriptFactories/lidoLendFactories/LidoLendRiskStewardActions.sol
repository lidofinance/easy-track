// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScripts to add or remove a risk steward for one Lido Lend market
contract LidoLendRiskStewardActions is TrustedCaller, IEVMScriptFactory {
    /// @dev Action ordinals are part of the calldata ABI. Never reorder existing members; append only.
    enum Action {
        AddRiskSteward,
        RemoveRiskSteward
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_STEWARD = "ZERO_STEWARD";
    string private constant ERROR_STEWARD_ALREADY_ADDED = "STEWARD_ALREADY_ADDED";
    string private constant ERROR_STEWARD_NOT_FOUND = "STEWARD_NOT_FOUND";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";
    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";

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

    /// @notice Creates an EVMScript for a risk steward action
    /// @param _creator Address who creates the EVMScript
    /// @param _evmScriptCallData Encoded tuple: (Action action, bytes payload), where payload is
    ///        abi.encode(bytes32 marketId, address steward)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (Action action, bytes memory payload) = decodeEVMScriptCallData(_evmScriptCallData);

        if (action == Action.AddRiskSteward) {
            return _createAddRiskStewardEVMScript(payload);
        }
        if (action == Action.RemoveRiskSteward) {
            return _createRemoveRiskStewardEVMScript(payload);
        }

        revert(ERROR_INVALID_ACTION);
    }

    /// @notice Decodes the action envelope used by createEVMScript
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (Action action, bytes memory payload)
    {
        (action, payload) = abi.decode(_evmScriptCallData, (Action, bytes));
    }

    /// @notice Decodes the typed payload shared by both risk steward actions
    function decodeRiskStewardPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, address steward)
    {
        (marketId, steward) = abi.decode(_payload, (bytes32, address));
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createAddRiskStewardEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address steward) = decodeRiskStewardPayload(_payload);
        require(steward != address(0), ERROR_ZERO_STEWARD);

        IRiskStewardDashboard dashboard = IRiskStewardDashboard(riskStewardDashboard);
        ILidoLend core = dashboard.LIDO_LEND();
        require(core.marketController(marketId) != address(0), ERROR_MARKET_NOT_FOUND);
        require(!dashboard.isMarketSteward(marketId, steward), ERROR_STEWARD_ALREADY_ADDED);

        return
            EVMScriptCreator.createEVMScript(
                riskStewardDashboard,
                dashboard.addMarketSteward.selector,
                abi.encode(marketId, steward)
            );
    }

    function _createRemoveRiskStewardEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address steward) = decodeRiskStewardPayload(_payload);

        IRiskStewardDashboard dashboard = IRiskStewardDashboard(riskStewardDashboard);
        ILidoLend core = dashboard.LIDO_LEND();
        require(core.marketController(marketId) != address(0), ERROR_MARKET_NOT_FOUND);
        require(dashboard.isMarketSteward(marketId, steward), ERROR_STEWARD_NOT_FOUND);

        return
            EVMScriptCreator.createEVMScript(
                riskStewardDashboard,
                dashboard.removeMarketSteward.selector,
                abi.encode(marketId, steward)
            );
    }
}
