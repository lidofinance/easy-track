// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IOperatorGrid.sol";
import "../../interfaces/ILido.sol";
import "../../interfaces/ILidoLocator.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to update group share limits in OperatorGrid
contract UpdateGroupsShareLimitInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_OPERATOR_GRID = "ZERO_OPERATOR_GRID";
    string private constant ERROR_EMPTY_NODE_OPERATORS = "EMPTY_NODE_OPERATORS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_NODE_OPERATOR = "ZERO_NODE_OPERATOR";
    string private constant ERROR_GROUP_NOT_EXISTS = "GROUP_NOT_EXISTS";
    string private constant ERROR_SHARE_LIMIT_TOO_HIGH = "SHARE_LIMIT_TOO_HIGH";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of OperatorGrid
    IOperatorGrid public immutable operatorGrid;

    // -------------
    // CONSTANTS
    // -------------

    uint256 internal constant TOTAL_BASIS_POINTS = 10000;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _operatorGrid)
        TrustedCaller(_trustedCaller)
    {
        require(_operatorGrid != address(0), ERROR_ZERO_OPERATOR_GRID);

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

        address toAddress = address(operatorGrid);
        bytes4 methodId = IOperatorGrid.updateGroupShareLimit.selector;
        bytes[] memory calldataArray = new bytes[](_nodeOperators.length);

        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            calldataArray[i] = abi.encode(_nodeOperators[i], _shareLimits[i]);
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
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
        require(_nodeOperators.length > 0, ERROR_EMPTY_NODE_OPERATORS);
        require(_nodeOperators.length == _shareLimits.length, ERROR_ARRAY_LENGTH_MISMATCH);

        uint256 maxSaneShareLimit = _maxSaneShareLimit();
        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            require(_nodeOperators[i] != address(0), ERROR_ZERO_NODE_OPERATOR);
            require(_shareLimits[i] <= maxSaneShareLimit, ERROR_SHARE_LIMIT_TOO_HIGH);

            IOperatorGrid.Group memory group = operatorGrid.group(_nodeOperators[i]);
            require(group.operator != address(0), ERROR_GROUP_NOT_EXISTS);
        }
    }

    /// @notice Calculates the maximum sane share limit (percent from Lido total shares)
    /// @return Maximum sane share limit
    function _maxSaneShareLimit() private view returns (uint256) {
        ILidoLocator locator = ILidoLocator(IOperatorGrid(operatorGrid).LIDO_LOCATOR());
        ILido lido = ILido(locator.lido());
        IVaultHub vaultHub = IVaultHub(locator.vaultHub());
        return (lido.getTotalShares() * vaultHub.MAX_RELATIVE_SHARE_LIMIT_BP()) / TOTAL_BASIS_POINTS;
    }
}
