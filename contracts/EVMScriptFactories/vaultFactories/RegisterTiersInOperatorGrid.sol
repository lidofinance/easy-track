// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to register multiple tiers in OperatorGrid
contract RegisterTiersInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of OperatorGrid
    IOperatorGrid public immutable operatorGrid;

    // -------------
    // CONSTANTS
    // -------------

    uint256 internal constant TOTAL_BASIS_POINTS = 10000;
    uint256 internal constant MAX_FEE_BP = type(uint16).max;

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

    /// @notice Creates EVMScript to register multiple tiers in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: (address[] _nodeOperators, IOperatorGrid.TierParams[][] _tiers)
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory _nodeOperators, IOperatorGrid.TierParams[][] memory _tiers) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_nodeOperators, _tiers);

        address toAddress = address(operatorGrid);
        bytes4 methodId = IOperatorGrid.registerTiers.selector;
        bytes[] memory calldataArray = new bytes[](_nodeOperators.length);

        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            calldataArray[i] = abi.encode(_nodeOperators[i], _tiers[i]);
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: (address[] _nodeOperators, IOperatorGrid.TierParams[][] _tiers)
    /// @return Node operator addresses and arrays of tier parameters which should be added to OperatorGrid
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, IOperatorGrid.TierParams[][] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, IOperatorGrid.TierParams[][] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], IOperatorGrid.TierParams[][]));
    }

    function _validateInputData(
        address[] memory _nodeOperators,
        IOperatorGrid.TierParams[][] memory _tiers
    ) private view {
        require(_nodeOperators.length > 0, "Empty node operators array");
        require(_nodeOperators.length == _tiers.length, "Array length mismatch");

        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            require(_nodeOperators[i] != address(0), "Zero node operator");
            require(_tiers[i].length > 0, "Empty tiers array");

            IOperatorGrid.Group memory group = operatorGrid.group(_nodeOperators[i]);
            require(group.operator != address(0), "Group not exists");

            // Validate tier parameters
            for (uint256 j = 0; j < _tiers[i].length; j++) {
                require(_tiers[i][j].shareLimit <= group.shareLimit, "Tier share limit too high");

                require(_tiers[i][j].reserveRatioBP != 0, "Zero reserve ratio");
                require(_tiers[i][j].reserveRatioBP <= TOTAL_BASIS_POINTS, "Reserve ratio too high");

                require(_tiers[i][j].forcedRebalanceThresholdBP != 0, "Zero forced rebalance threshold");
                require(_tiers[i][j].forcedRebalanceThresholdBP <= _tiers[i][j].reserveRatioBP, "Forced rebalance threshold too high");

                require(_tiers[i][j].infraFeeBP <= MAX_FEE_BP, "Infra fee too high");
                require(_tiers[i][j].liquidityFeeBP <= MAX_FEE_BP, "Liquidity fee too high");
                require(_tiers[i][j].reservationFeeBP <= MAX_FEE_BP, "Reservation fee too high");
            }
        }
    }
}
