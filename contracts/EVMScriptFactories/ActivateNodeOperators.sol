// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function activateNodeOperator(uint256 _nodeOperatorId) external;
}

/// @notice Creates EVMScript to activate several node operator
contract ActivateNodeOperators is TrustedCaller, IEVMScriptFactory {
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
        uint256[] memory decodedCallData = abi.decode(_evmScriptCallData, (uint256[]));
        bytes[] memory nodeOperatorsIdsCalldata = new bytes[](decodedCallData.length);

        for (uint i = 0; i < decodedCallData.length; i++) {
            nodeOperatorsIdsCalldata[i] = abi.encode(decodedCallData[i]);
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.activateNodeOperator.selector,
                nodeOperatorsIdsCalldata
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (uint256[] memory nodeOperatorIds) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (uint256[] memory nodeOperatorIds) {
        return abi.decode(_evmScriptCallData, (uint256[]));
    }
}
