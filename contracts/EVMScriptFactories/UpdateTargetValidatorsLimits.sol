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

    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";

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
        bytes[] memory updateTargetLimitsCallData = new bytes[](decodedCallData.length);

        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint i = 0; i < decodedCallData.length; i++) {
            require(
                decodedCallData[i].nodeOperatorId < nodeOperatorsCount,
                ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );
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
}
