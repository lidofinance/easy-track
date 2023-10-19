// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorRegestry.sol";

/// @notice Creates EVMScript to set node operators target validators limit
contract UpdateTargetValidatorLimits is TrustedCaller, IEVMScriptFactory {
    struct TargetValidatorsLimit {
        uint256 nodeOperatorId;
        bool isTargetLimitActive;
        uint256 targetLimit;
    }

    // -------------
    // CONSTANTS
    // -------------

    uint256 internal constant UINT64_MAX = 0xFFFFFFFFFFFFFFFF;

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant ERROR_NODE_OPERATORS_IS_NOT_SORTED = "NODE_OPERATORS_IS_NOT_SORTED";
    string private constant ERROR_TARGET_LIMIT_GREATER_THEN_UINT64 = "TARGET_LIMIT_GREATER_THEN_UINT64";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _nodeOperatorsRegistry
    ) TrustedCaller(_trustedCaller) {
        nodeOperatorsRegistry = INodeOperatorsRegistry(_nodeOperatorsRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        TargetValidatorsLimit[] memory decodedCallData = abi.decode(
            _evmScriptCallData,
            (TargetValidatorsLimit[])
        );

        _validateInputData(decodedCallData);

        bytes[] memory updateTargetLimitsCallData = new bytes[](decodedCallData.length);

        for (uint256 i = 0; i < decodedCallData.length; i++) {
            updateTargetLimitsCallData[i] = abi.encode(decodedCallData[i]);
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.updateTargetValidatorsLimits.selector,
                updateTargetLimitsCallData
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (TargetValidatorsLimit[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (TargetValidatorsLimit[] memory) {
        return abi.decode(_evmScriptCallData, (TargetValidatorsLimit[]));
    }

    function _validateInputData(TargetValidatorsLimit[] memory _decodedCallData) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint256 i = 0; i < _decodedCallData.length; i++) {
            require(
                i == 0 ||
                    _decodedCallData[i].nodeOperatorId > _decodedCallData[i - 1].nodeOperatorId,
                ERROR_NODE_OPERATORS_IS_NOT_SORTED
            );
            require(
                _decodedCallData[i].nodeOperatorId < nodeOperatorsCount,
                ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );
            require(
                _decodedCallData[i].targetLimit <= UINT64_MAX,
                ERROR_TARGET_LIMIT_GREATER_THEN_UINT64
            );
        }
    }
}
