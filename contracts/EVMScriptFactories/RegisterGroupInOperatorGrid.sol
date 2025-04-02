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
    error ZeroGroupId();
    error ZeroShareLimit();

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of OperatorGrid
    IOperatorGrid public immutable operatorGrid;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _operatorGrid)
    // TODO - is trusted caller needed here?
        TrustedCaller(_trustedCaller)
    {
        operatorGrid = IOperatorGrid(_operatorGrid);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to register a group in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256 groupId, uint256 shareLimit
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (uint256 groupId, uint256 shareLimit) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(groupId, shareLimit);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.registerGroup.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256 groupId, uint256 shareLimit
    /// @return Group ID and share limit which should be added to operator grid
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

    function _validateInputData(
        uint256 groupId,
        uint256 shareLimit
    ) private view {
        if (groupId == 0) revert ZeroGroupId();
        if (shareLimit == 0) revert ZeroShareLimit();

        Group memory group = operatorGrid.group(groupId);
        if (group.id > 0) revert GroupExists();

        // TODO - add check for share limit
    }
}
