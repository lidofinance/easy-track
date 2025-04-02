// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to update group share limit in OperatorGrid
contract UpdateGroupShareLimitInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    error GroupNotExists();

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

    /// @notice Creates EVMScript to update group share limit in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256 groupId, uint256 newShareLimit
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (uint256 groupId, uint256 newShareLimit) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(groupId);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.updateGroupShareLimit.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256 groupId, uint256 newShareLimit
    /// @return Group ID and new share limit which should be updated in operator grid
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (uint256, uint256)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (uint256, uint256)
    {
        return abi.decode(_evmScriptCallData, (uint256, uint256));
    }

    function _validateInputData(uint256 groupId) private view {
        IOperatorGrid.Group memory group = operatorGrid.group(groupId);
        if (group.id == 0) revert GroupNotExists();
        // TODO - add check for new share limit
    }
} 