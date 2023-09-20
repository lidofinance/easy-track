// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function setNodeOperatorRewardAddress(uint256 _nodeOperatorId, address _rewardAddress) external;

    function MAX_NODE_OPERATOR_NAME_LENGTH() external view returns (uint256);

    function getNodeOperatorsCount() external view returns (uint256);

    function getLocator() external view returns (ILidoLocator);
}

interface ILidoLocator {
    function lido() external view returns (address);
}

/// @notice Creates EVMScript to set node operators reward address
contract SetNodeOperatorRewardAddresses is TrustedCaller, IEVMScriptFactory {
    struct SetRewardAddressInput {
        uint256 nodeOperatorId;
        address rewardAddress;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant NODE_OPERATOR_INDEX_OUT_OF_RANGE = "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant LIDO_REWARD_ADDRESS = "LIDO_REWARD_ADDRESS";
    string private constant ZERO_REWARD_ADDRESS = "ZERO_REWARD_ADDRESS";

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
        SetRewardAddressInput[] memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(decodedCallData);

        bytes[] memory nodeOperatorRewardAddressesCalldata = new bytes[](decodedCallData.length);

        for (uint i = 0; i < decodedCallData.length; i++) {
            nodeOperatorRewardAddressesCalldata[i] = abi.encode(
                decodedCallData[i].nodeOperatorId,
                decodedCallData[i].rewardAddress
            );
        }
        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.setNodeOperatorRewardAddress.selector,
                nodeOperatorRewardAddressesCalldata
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (SetRewardAddressInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (SetRewardAddressInput[] memory) {
        return abi.decode(_evmScriptCallData, (SetRewardAddressInput[]));
    }

    function _validateInputData(SetRewardAddressInput[] memory _nodeOperatorRewardAddressesInput) private view {
        address lido = nodeOperatorsRegistry.getLocator().lido();

        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint i = 0; i < _nodeOperatorRewardAddressesInput.length; i++) {
            require(
                _nodeOperatorRewardAddressesInput[i].nodeOperatorId < nodeOperatorsCount,
                NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );
            
            require(_nodeOperatorRewardAddressesInput[i].rewardAddress != lido, LIDO_REWARD_ADDRESS);
            require(_nodeOperatorRewardAddressesInput[i].rewardAddress != address(0), ZERO_REWARD_ADDRESS);
        }
    }
}