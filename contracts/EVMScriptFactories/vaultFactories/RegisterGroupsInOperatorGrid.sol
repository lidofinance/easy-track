// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to register a group and its tiers in OperatorGrid
contract RegisterGroupsInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_OPERATOR_GRID = "ZERO_OPERATOR_GRID";
    string private constant ERROR_EMPTY_NODE_OPERATORS = "EMPTY_NODE_OPERATORS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_NODE_OPERATOR = "ZERO_NODE_OPERATOR";
    string private constant ERROR_DEFAULT_TIER_OPERATOR = "DEFAULT_TIER_OPERATOR";
    string private constant ERROR_EMPTY_TIERS = "EMPTY_TIERS";
    string private constant ERROR_GROUP_EXISTS = "GROUP_EXISTS";
    string private constant ERROR_GROUP_SHARE_LIMIT_TOO_HIGH = "GROUP_SHARE_LIMIT_TOO_HIGH";
    string private constant ERROR_TIER_SHARE_LIMIT_TOO_HIGH = "TIER_SHARE_LIMIT_TOO_HIGH";
    string private constant ERROR_ZERO_RESERVE_RATIO = "ZERO_RESERVE_RATIO";
    string private constant ERROR_RESERVE_RATIO_TOO_HIGH = "RESERVE_RATIO_TOO_HIGH";
    string private constant ERROR_ZERO_FORCED_REBALANCE_THRESHOLD = "ZERO_FORCED_REBALANCE_THRESHOLD";
    string private constant ERROR_FORCED_REBALANCE_THRESHOLD_TOO_HIGH = "FORCED_REBALANCE_THRESHOLD_TOO_HIGH";
    string private constant ERROR_INFRA_FEE_TOO_HIGH = "INFRA_FEE_TOO_HIGH";
    string private constant ERROR_LIQUIDITY_FEE_TOO_HIGH = "LIQUIDITY_FEE_TOO_HIGH";
    string private constant ERROR_RESERVATION_FEE_TOO_HIGH = "RESERVATION_FEE_TOO_HIGH";
    string private constant ERROR_ZERO_MAX_SHARE_LIMIT = "ZERO_MAX_SHARE_LIMIT";
    string private constant ERROR_ASCENDING_ORDER_IN_OPERATORS_ARRAY = "ASCENDING_ORDER_IN_OPERATORS_ARRAY";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of OperatorGrid
    IOperatorGrid public immutable operatorGrid;

    /// @notice Maximum sane share limit (percent from Lido total shares)
    uint256 public immutable maxSaneShareLimit;

    // -------------
    // CONSTANTS
    // -------------

    uint256 internal constant TOTAL_BASIS_POINTS = 10000;
    uint256 internal constant MAX_FEE_BP = type(uint16).max;
    /// @notice Special address to denote that default tier is not linked to any real operator
    address public constant DEFAULT_TIER_OPERATOR = address(uint160(type(uint160).max));

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _operatorGrid, uint256 _maxSaneShareLimit)
        TrustedCaller(_trustedCaller)
    {
        require(_operatorGrid != address(0), ERROR_ZERO_OPERATOR_GRID);
        require(_maxSaneShareLimit > 0, ERROR_ZERO_MAX_SHARE_LIMIT);

        operatorGrid = IOperatorGrid(_operatorGrid);
        maxSaneShareLimit = _maxSaneShareLimit;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to register multiple groups and their tiers in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: (address[] _nodeOperators, uint256[] _shareLimits, TierParams[][] _tiers)
    /// @dev Node operators must be in ascending order (no duplicates allowed)
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory _nodeOperators,
            uint256[] memory _shareLimits,
            TierParams[][] memory _tiers
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_nodeOperators, _shareLimits, _tiers);
        
        // Each group requires 2 calls (registerGroup and registerTiers)
        uint256 totalCalls = _nodeOperators.length * 2;
        address toAddress = address(operatorGrid);
        bytes4[] memory methodIds = new bytes4[](totalCalls);
        bytes[] memory calldataArray = new bytes[](totalCalls);

        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            // Register group
            methodIds[i * 2] = IOperatorGrid.registerGroup.selector;
            calldataArray[i * 2] = abi.encode(_nodeOperators[i], _shareLimits[i]);

            // Register tiers
            methodIds[i * 2 + 1] = IOperatorGrid.registerTiers.selector;
            calldataArray[i * 2 + 1] = abi.encode(_nodeOperators[i], _tiers[i]);
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodIds, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: (address[] _nodeOperators, uint256[] _shareLimits, TierParams[][] _tiers)
    /// @return NodeOperator addresses, group share limits and arrays of tier parameters
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, uint256[] memory, TierParams[][] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, uint256[] memory, TierParams[][] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[], TierParams[][]));
    }

    function _validateInputData(
        address[] memory _nodeOperators,
        uint256[] memory _shareLimits,
        TierParams[][] memory _tiers
    ) private view {
        require(_nodeOperators.length > 0, ERROR_EMPTY_NODE_OPERATORS);
        require(
            _nodeOperators.length == _shareLimits.length &&
            _nodeOperators.length == _tiers.length,
            ERROR_ARRAY_LENGTH_MISMATCH
        );

        // Check for ascending order in node operators array (no duplicates allowed)
        for (uint256 i = 0; i < _nodeOperators.length - 1; i++) {
            require(_nodeOperators[i] < _nodeOperators[i+1], ERROR_ASCENDING_ORDER_IN_OPERATORS_ARRAY);
        }

        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            require(_nodeOperators[i] != address(0), ERROR_ZERO_NODE_OPERATOR);
            require(_nodeOperators[i] != DEFAULT_TIER_OPERATOR, ERROR_DEFAULT_TIER_OPERATOR);
            require(_tiers[i].length > 0, ERROR_EMPTY_TIERS);

            IOperatorGrid.Group memory group = operatorGrid.group(_nodeOperators[i]);
            require(group.operator == address(0), ERROR_GROUP_EXISTS);

            require(_shareLimits[i] <= maxSaneShareLimit, ERROR_GROUP_SHARE_LIMIT_TOO_HIGH);

            // Validate tier parameters
            for (uint256 j = 0; j < _tiers[i].length; j++) {
                require(_tiers[i][j].shareLimit <= _shareLimits[i], ERROR_TIER_SHARE_LIMIT_TOO_HIGH);

                require(_tiers[i][j].reserveRatioBP != 0, ERROR_ZERO_RESERVE_RATIO);
                require(_tiers[i][j].reserveRatioBP <= TOTAL_BASIS_POINTS, ERROR_RESERVE_RATIO_TOO_HIGH);

                require(_tiers[i][j].forcedRebalanceThresholdBP != 0, ERROR_ZERO_FORCED_REBALANCE_THRESHOLD);
                require(_tiers[i][j].forcedRebalanceThresholdBP <= _tiers[i][j].reserveRatioBP, ERROR_FORCED_REBALANCE_THRESHOLD_TOO_HIGH);

                require(_tiers[i][j].infraFeeBP <= MAX_FEE_BP, ERROR_INFRA_FEE_TOO_HIGH);
                require(_tiers[i][j].liquidityFeeBP <= MAX_FEE_BP, ERROR_LIQUIDITY_FEE_TOO_HIGH);
                require(_tiers[i][j].reservationFeeBP <= MAX_FEE_BP, ERROR_RESERVATION_FEE_TOO_HIGH);
            }
        }
    }
}
