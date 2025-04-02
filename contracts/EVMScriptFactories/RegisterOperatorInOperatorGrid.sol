// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to register an operator in OperatorGrid
contract RegisterOperatorInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    error GroupNotExists();
    error OperatorExists();
    error ZeroOperatorAddress();
    error ZeroGroupId();

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

    /// @notice Creates EVMScript to register an operator in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address operator, uint256 groupId
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address operatorAddr, uint256 groupId) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(operatorAddr, groupId);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.registerOperator.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address operator, uint256 groupId
    /// @return Operator address and group ID which should be added to operator grid
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

    function _validateInputData(address operatorAddr, uint256 groupId) private view {
        if (operatorAddr == address(0)) revert ZeroOperatorAddress();
        if (groupId == 0) revert ZeroGroupId();
        
        IOperatorGrid.Group memory group = operatorGrid.group(groupId);
        if (group.id == 0) revert GroupNotExists();
        
        // TODO - add check for operator existence
    }
} 