// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IOperatorGrid.sol";

/// @author dry914
/// @notice Creates EVMScript to register a tier in OperatorGrid
contract RegisterTierInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    error GroupNotExists();
    error TierExists();

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

    /// @notice Creates EVMScript to register a tier in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256 groupId, uint256 tierId, uint256 shareLimit, uint256 reserveRatioBP, uint256 rebalanceThresholdBP, uint256 treasuryFeeBP
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            uint256 groupId,
            uint256 tierId,
            // TODO - add validation for other parameters
            uint256 shareLimit,
            uint256 reserveRatioBP,
            uint256 rebalanceThresholdBP,
            uint256 treasuryFeeBP
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(groupId, tierId);

        return
            EVMScriptCreator.createEVMScript(
                address(operatorGrid),
                IOperatorGrid.registerTier.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256 groupId, uint256 tierId, uint256 shareLimit, uint256 reserveRatioBP, uint256 rebalanceThresholdBP, uint256 treasuryFeeBP
    /// @return Group ID, tier ID, share limit, reserve ratio, rebalance threshold, and treasury fee which should be added to operator grid
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            uint256,
            uint256,
            uint256,
            uint256,
            uint256,
            uint256
        )
    {
        return abi.decode(
            _evmScriptCallData,
            (uint256, uint256, uint256, uint256, uint256, uint256)
        );
    }

    function _validateInputData(uint256 groupId, uint256 tierId) private view {
        IOperatorGrid.Group memory group = operatorGrid.group(groupId);
        if (group.id == 0) revert GroupNotExists();
        // TODO - add check for tier existence
        // TODO - add validation for other parameters
    }
} 