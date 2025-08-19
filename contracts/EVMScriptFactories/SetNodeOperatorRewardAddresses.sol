// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorsRegistry.sol";

/// @notice Creates EVMScript to set reward address of several node operators
contract SetNodeOperatorRewardAddresses is TrustedCaller, IEVMScriptFactory {
    struct SetRewardAddressInput {
        uint256 nodeOperatorId;
        address rewardAddress;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant ERROR_LIDO_REWARD_ADDRESS = "LIDO_REWARD_ADDRESS";
    string private constant ERROR_ZERO_REWARD_ADDRESS = "ZERO_REWARD_ADDRESS";
    string private constant ERROR_SAME_REWARD_ADDRESS = "SAME_REWARD_ADDRESS";
    string private constant ERROR_NODE_OPERATORS_IS_NOT_SORTED = "NODE_OPERATORS_IS_NOT_SORTED";
    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;
    /// @notice Address of Lido contract
    address public immutable lido;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _nodeOperatorsRegistry,
        address _lido
    ) TrustedCaller(_trustedCaller) {
        nodeOperatorsRegistry = INodeOperatorsRegistry(_nodeOperatorsRegistry);
        lido = _lido;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set reward address of several node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (SetRewardAddressInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        SetRewardAddressInput[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        _validateInputData(decodedCallData);

        bytes[] memory nodeOperatorRewardAddressesCalldata = new bytes[](decodedCallData.length);

        for (uint256 i = 0; i < decodedCallData.length; ++i) {
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

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (SetRewardAddressInput[])
    /// @return SetRewardAddressInput[]
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

    function _validateInputData(SetRewardAddressInput[] memory _decodedCallData) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        require(_decodedCallData.length > 0, ERROR_EMPTY_CALLDATA);
        require(
            _decodedCallData[_decodedCallData.length - 1].nodeOperatorId < nodeOperatorsCount,
            ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE
        );

        for (uint256 i = 0; i < _decodedCallData.length; ++i) {
            require(
                i == 0 ||
                    _decodedCallData[i].nodeOperatorId > _decodedCallData[i - 1].nodeOperatorId,
                ERROR_NODE_OPERATORS_IS_NOT_SORTED
            );
            require(_decodedCallData[i].rewardAddress != lido, ERROR_LIDO_REWARD_ADDRESS);
            require(_decodedCallData[i].rewardAddress != address(0), ERROR_ZERO_REWARD_ADDRESS);

            (
                /* bool active */,
                /* string memory name */,
                address rewardAddress,
                /* uint64 stakingLimit */,
                /* uint64 stoppedValidators */,
                /* uint64 totalSigningKeys */,
                /* uint64 usedSigningKeys */
            ) = nodeOperatorsRegistry.getNodeOperator(
                _decodedCallData[i].nodeOperatorId,
                false
            );            
            
            require(_decodedCallData[i].rewardAddress != rewardAddress, ERROR_SAME_REWARD_ADDRESS);
        }
    }
}
