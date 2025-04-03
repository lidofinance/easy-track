// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to register multiple tiers in OperatorGrid
contract RegisterTiersInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    error GroupNotExists();
    error ZeroNodeOperator();
    error EmptyTiersArray();

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
        operatorGrid = IOperatorGrid(_operatorGrid);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to register multiple tiers in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address nodeOperator, IOperatorGrid.TierParams[] tiers
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address nodeOperator, IOperatorGrid.TierParams[] memory tiers) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(nodeOperator, tiers);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.registerTiers.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address nodeOperator, IOperatorGrid.TierParams[] tiers
    /// @return Node operator address and array of tier parameters which should be added to operator grid
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address, IOperatorGrid.TierParams[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address, IOperatorGrid.TierParams[] memory)
    {
        return abi.decode(_evmScriptCallData, (address, IOperatorGrid.TierParams[]));
    }

    function _validateInputData(address nodeOperator, IOperatorGrid.TierParams[] memory tiers) private view {
        if (nodeOperator == address(0)) revert ZeroNodeOperator();
        if (tiers.length == 0) revert EmptyTiersArray();

        IOperatorGrid.Group memory group = operatorGrid.group(nodeOperator);
        if (group.operator == address(0)) revert GroupNotExists();
    }
} 