// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to register a group and its tiers in OperatorGrid
contract RegisterGroupInOperatorGrid is TrustedCaller, IEVMScriptFactory {

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

    /// @notice Creates EVMScript to register a group and its tiers in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address _nodeOperator, uint256 _shareLimit, IOperatorGrid.TierParams[] _tiers
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address _nodeOperator, uint256 _shareLimit, IOperatorGrid.TierParams[] memory _tiers) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_nodeOperator, _tiers);
        
        // Create method selectors
        bytes4[] memory methodIds = new bytes4[](2);
        methodIds[0] = IOperatorGrid.registerGroup.selector;
        methodIds[1] = IOperatorGrid.registerTiers.selector;

        // Create calldata for both registerGroup and registerTiers calls
        bytes[] memory calldataArray = new bytes[](2);
        calldataArray[0] = abi.encode(_nodeOperator, _shareLimit);
        calldataArray[1] = abi.encode(_nodeOperator, _tiers);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                methodIds,
                calldataArray
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address _nodeOperator, uint256 _shareLimit, IOperatorGrid.TierParams[] _tiers
    /// @return Node operator address, share limit and array of tier parameters which should be added to operator grid
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address, uint256, IOperatorGrid.TierParams[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address, uint256, IOperatorGrid.TierParams[] memory)
    {
        return abi.decode(_evmScriptCallData, (address, uint256, IOperatorGrid.TierParams[]));
    }

    function _validateInputData(
        address _nodeOperator,
        IOperatorGrid.TierParams[] memory _tiers
    ) private view {
        require(_nodeOperator != address(0), "Zero node operator");
        require(_tiers.length > 0, "Empty tiers array");

        IOperatorGrid.Group memory group = operatorGrid.group(_nodeOperator);
        require(group.operator == address(0), "Group exists");
    }
}
