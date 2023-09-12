// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function setNodeOperatorRewardAddress(uint256 _nodeOperatorId, address _rewardAddress) external;

    function getNodeOperatorsCount() external view returns (uint256);
}

/// @notice Creates EVMScript to set node operators reward address
contract SetNodeOperatorRewardAddress is TrustedCaller, IEVMScriptFactory {
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
        (uint256 nodeOperatorId, ) = abi.decode(
            _evmScriptCallData,
            (uint256, address)
        );
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        require(nodeOperatorId < nodeOperatorsCount, ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE);

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.setNodeOperatorRewardAddress.selector,
                _evmScriptCallData
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (uint256 nodeOperatorId, address rewardAddress) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (uint256 nodeOperatorId, address rewardAddress) {
        return abi.decode(_evmScriptCallData, (uint256, address));
    }
}
