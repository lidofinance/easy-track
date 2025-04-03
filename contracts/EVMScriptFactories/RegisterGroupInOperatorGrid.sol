// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to register a group in OperatorGrid
contract RegisterGroupInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    error GroupExists();
    error ZeroNodeOperator();

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

    /// @notice Creates EVMScript to register a group in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address nodeOperator, uint256 shareLimit
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address nodeOperator,) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(nodeOperator);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.registerGroup.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address nodeOperator, uint256 shareLimit
    /// @return Node operator address and share limit which should be added to operator grid
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address, uint256)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address, uint256)
    {
        return abi.decode(_evmScriptCallData, (address, uint256));
    }

    function _validateInputData(
        address nodeOperator
    ) private view {
        if (nodeOperator == address(0)) revert ZeroNodeOperator();

        IOperatorGrid.Group memory group = operatorGrid.group(nodeOperator);
        if (group.operator != address(0)) revert GroupExists();
    }
}
