// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to alter tiers in OperatorGrid
contract AlterTiersInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // CONSTANTS
    // -------------

    /// @dev max value for fees in basis points - it's about 650%
    uint256 internal constant MAX_FEE_BP = type(uint16).max;
    uint256 internal constant TOTAL_BASIS_POINTS = 10000;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of OperatorGrid
    IOperatorGrid public immutable operatorGrid;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _operatorGrid)
        TrustedCaller(_trustedCaller)
    {
        require(_operatorGrid != address(0), "Zero operator grid");

        operatorGrid = IOperatorGrid(_operatorGrid);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to alter tiers in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256[] _tierIds, IOperatorGrid.TierParams[] _tierParams
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (uint256[] memory _tierIds, IOperatorGrid.TierParams[] memory _tierParams) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_tierIds, _tierParams);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.alterTiers.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256[] _tierIds, IOperatorGrid.TierParams[] _tierParams
    /// @return Tier IDs and tier parameters which should be updated in OperatorGrid
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (uint256[] memory, IOperatorGrid.TierParams[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (uint256[] memory, IOperatorGrid.TierParams[] memory)
    {
        return abi.decode(_evmScriptCallData, (uint256[], IOperatorGrid.TierParams[]));
    }

    function _validateInputData(uint256[] memory _tierIds, IOperatorGrid.TierParams[] memory _tierParams) private view {
        require(_tierIds.length > 0, "Empty tier IDs array");
        require(_tierIds.length == _tierParams.length, "Array length mismatch");

        // Validate tier parameters
        for (uint256 i = 0; i < _tierIds.length; i++) {
            IOperatorGrid.Tier memory tier = operatorGrid.tier(_tierIds[i]); // reverts if tier does not exist in the operator grid
            IOperatorGrid.Group memory group = operatorGrid.group(tier.operator);
            require(_tierParams[i].shareLimit <= group.shareLimit, "Tier share limit too high");

            require(_tierParams[i].reserveRatioBP != 0, "Zero reserve ratio");
            require(_tierParams[i].reserveRatioBP <= TOTAL_BASIS_POINTS, "Reserve ratio too high");

            require(_tierParams[i].forcedRebalanceThresholdBP != 0, "Zero forced rebalance threshold");
            require(_tierParams[i].forcedRebalanceThresholdBP <= _tierParams[i].reserveRatioBP, "Forced rebalance threshold too high");

            require(_tierParams[i].infraFeeBP <= MAX_FEE_BP, "Infra fee too high");
            require(_tierParams[i].liquidityFeeBP <= MAX_FEE_BP, "Liquidity fee too high");
            require(_tierParams[i].reservationFeeBP <= MAX_FEE_BP, "Reservation fee too high");
        }
    }
}
