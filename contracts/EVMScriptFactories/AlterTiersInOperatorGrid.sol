// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to alter tiers in OperatorGrid
contract AlterTiersInOperatorGrid is TrustedCaller, IEVMScriptFactory {

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

    /// @notice Creates EVMScript to alter tiers in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256[] _tierIds, IOperatorGrid.TierParams[] _tierParams
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (uint256[] memory _tierIds, IOperatorGrid.TierParams[] memory _tierParams) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_tierIds, _tierParams);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.alterTiers.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256[] _tierIds, IOperatorGrid.TierParams[] _tierParams
    /// @return Tier IDs and tier parameters which should be updated in OperatorGrid
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (uint256[] memory, IOperatorGrid.TierParams[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (uint256[] memory, IOperatorGrid.TierParams[] memory)
    {
        return abi.decode(_evmScriptCallData, (uint256[], IOperatorGrid.TierParams[]));
    }

    function _validateInputData(uint256[] memory _tierIds, IOperatorGrid.TierParams[] memory _tierParams) private view {
        require(_tierIds.length > 0, "Empty tier IDs array");
        require(_tierIds.length == _tierParams.length, "Array length mismatch");
        
        uint256 _tiersCount = operatorGrid.tiersCount();
        for (uint256 i = 0; i < _tierIds.length; i++) {
            require(_tierIds[i] < _tiersCount, "Tier not exists");
        }
    }
} 