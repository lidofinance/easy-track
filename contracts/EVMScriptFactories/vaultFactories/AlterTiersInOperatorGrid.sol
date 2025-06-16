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
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_OPERATOR_GRID = "ZERO_OPERATOR_GRID";
    string private constant ERROR_EMPTY_TIER_IDS = "EMPTY_TIER_IDS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_TIER_SHARE_LIMIT_TOO_HIGH = "TIER_SHARE_LIMIT_TOO_HIGH";
    string private constant ERROR_ZERO_RESERVE_RATIO = "ZERO_RESERVE_RATIO";
    string private constant ERROR_RESERVE_RATIO_TOO_HIGH = "RESERVE_RATIO_TOO_HIGH";
    string private constant ERROR_ZERO_FORCED_REBALANCE_THRESHOLD = "ZERO_FORCED_REBALANCE_THRESHOLD";
    string private constant ERROR_FORCED_REBALANCE_THRESHOLD_TOO_HIGH = "FORCED_REBALANCE_THRESHOLD_TOO_HIGH";
    string private constant ERROR_INFRA_FEE_TOO_HIGH = "INFRA_FEE_TOO_HIGH";
    string private constant ERROR_LIQUIDITY_FEE_TOO_HIGH = "LIQUIDITY_FEE_TOO_HIGH";
    string private constant ERROR_RESERVATION_FEE_TOO_HIGH = "RESERVATION_FEE_TOO_HIGH";

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
        require(_operatorGrid != address(0), ERROR_ZERO_OPERATOR_GRID);

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
        require(_tierIds.length > 0, ERROR_EMPTY_TIER_IDS);
        require(_tierIds.length == _tierParams.length, ERROR_ARRAY_LENGTH_MISMATCH);

        // Validate tier parameters
        for (uint256 i = 0; i < _tierIds.length; i++) {
            IOperatorGrid.Tier memory tier = operatorGrid.tier(_tierIds[i]); // reverts if tier does not exist in the operator grid
            IOperatorGrid.Group memory group = operatorGrid.group(tier.operator);
            require(_tierParams[i].shareLimit <= group.shareLimit, ERROR_TIER_SHARE_LIMIT_TOO_HIGH);

            require(_tierParams[i].reserveRatioBP != 0, ERROR_ZERO_RESERVE_RATIO);
            require(_tierParams[i].reserveRatioBP <= TOTAL_BASIS_POINTS, ERROR_RESERVE_RATIO_TOO_HIGH);

            require(_tierParams[i].forcedRebalanceThresholdBP != 0, ERROR_ZERO_FORCED_REBALANCE_THRESHOLD);
            require(_tierParams[i].forcedRebalanceThresholdBP <= _tierParams[i].reserveRatioBP, ERROR_FORCED_REBALANCE_THRESHOLD_TOO_HIGH);

            require(_tierParams[i].infraFeeBP <= MAX_FEE_BP, ERROR_INFRA_FEE_TOO_HIGH);
            require(_tierParams[i].liquidityFeeBP <= MAX_FEE_BP, ERROR_LIQUIDITY_FEE_TOO_HIGH);
            require(_tierParams[i].reservationFeeBP <= MAX_FEE_BP, ERROR_RESERVATION_FEE_TOO_HIGH);
        }
    }
}
