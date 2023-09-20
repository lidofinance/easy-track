// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function updateTargetValidatorsLimits(
        uint256 _nodeOperatorId,
        bool _isTargetLimitActive,
        uint256 _targetLimit
    ) external;

    function getNodeOperatorsCount() external view returns (uint256);
}

/// @notice Creates EVMScript to set node operators reward address
contract UpdateTargetValidatorsLimits is TrustedCaller, IEVMScriptFactory {
    struct TargetValidatorsLimit {
        uint256 nodeOperatorId;
        bool isTargetLimitActive;
        uint256 targetLimit;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant NODE_OPERATOR_INDEX_OUT_OF_RANGE = "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant TARGET_LIMIT_EXCEEDED = "TARGET_LIMIT_EXCEEDED";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;

    // -------------
    // CONSTANTS
    // -------------

    uint256 internal constant UINT64_MAX = 0xFFFFFFFFFFFFFFFF;

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

        for (uint i = 0; i < decodedCallData.length; i++) {
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

    function _validateInputData(
        TargetValidatorsLimit[] memory _targetValidatorsLimitInput
    ) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint i = 0; i < _targetValidatorsLimitInput.length; i++) {
            require(
                _targetValidatorsLimitInput[i].nodeOperatorId < nodeOperatorsCount,
                NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );

            if (_targetValidatorsLimitInput[i].isTargetLimitActive == true)
                require(
                    _targetValidatorsLimitInput[i].targetLimit < UINT64_MAX,
                    TARGET_LIMIT_EXCEEDED
                );
        }
    }
}
