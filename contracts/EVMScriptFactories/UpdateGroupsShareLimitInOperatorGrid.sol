// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to update group share limits in OperatorGrid
contract UpdateGroupsShareLimitInOperatorGrid is TrustedCaller, IEVMScriptFactory {

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

    /// @notice Creates EVMScript to update group share limits in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address[] _nodeOperators, uint256[] _shareLimits
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory _nodeOperators, uint256[] memory _shareLimits) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_nodeOperators, _shareLimits);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.updateGroupsShareLimit.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _nodeOperators, uint256[] _shareLimits
    /// @return Node operator addresses and new share limits which should be updated in OperatorGrid
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, uint256[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, uint256[] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[]));
    }

    function _validateInputData(address[] memory _nodeOperators, uint256[] memory _shareLimits) private view {
        require(_nodeOperators.length > 0, "Empty node operators array");
        require(_nodeOperators.length == _shareLimits.length, "Array length mismatch");

        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            require(_nodeOperators[i] != address(0), "Zero node operator");

            IOperatorGrid.Group memory group = operatorGrid.group(_nodeOperators[i]);
            require(group.operator != address(0), "Group not exists");
        }
    }
}
