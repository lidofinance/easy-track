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
        }
    }
}
