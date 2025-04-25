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
    /// @param _evmScriptCallData Encoded: address _nodeOperator, IOperatorGrid.TierParams[] _tiers
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address _nodeOperator, IOperatorGrid.TierParams[] memory _tiers) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_nodeOperator, _tiers);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.registerTiers.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address _nodeOperator, IOperatorGrid.TierParams[] _tiers
    /// @return Node operator address and array of tier parameters which should be added to OperatorGrid
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

    function _validateInputData(address _nodeOperator, IOperatorGrid.TierParams[] memory _tiers) private view {
        require(_nodeOperator != address(0), "Zero node operator");
        require(_tiers.length > 0, "Empty tiers array");

        IOperatorGrid.Group memory group = operatorGrid.group(_nodeOperator);
        require(group.operator != address(0), "Group not exists");
    }
} 