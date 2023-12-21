// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorsRegistry.sol";

/// @notice Creates EVMScript to set staking limit for node operators
contract SetVettedValidatorsLimits is TrustedCaller, IEVMScriptFactory {
    struct VettedValidatorsLimitInput {
        uint256 nodeOperatorId;
        uint256 stakingLimit;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_NOT_ENOUGH_SIGNING_KEYS = "NOT_ENOUGH_SIGNING_KEYS";
    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant ERROR_NODE_OPERATORS_IS_NOT_SORTED = "NODE_OPERATORS_IS_NOT_SORTED";
    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";
    string private constant ERROR_NODE_OPERATOR_IS_NOT_ACTIVE = "NODE_OPERATOR_IS_NOT_ACTIVE";

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

    /// @notice Creates EVMScript to set staking limit of several node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (VettedValidatorsLimitInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        VettedValidatorsLimitInput[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        _validateInputData(decodedCallData);

        bytes[] memory setVettedValidatorsLimitsCalldata = new bytes[](decodedCallData.length);

        for (uint256 i = 0; i < decodedCallData.length; ++i) {
            setVettedValidatorsLimitsCalldata[i] = abi.encode(
                decodedCallData[i].nodeOperatorId,
                decodedCallData[i].stakingLimit
            );
        }

        return
            EVMScriptCreator.createEVMScript(
                address(nodeOperatorsRegistry),
                nodeOperatorsRegistry.setNodeOperatorStakingLimit.selector,
                setVettedValidatorsLimitsCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (VettedValidatorsLimitInput[])
    /// @return VettedValidatorsLimitInput[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (VettedValidatorsLimitInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (VettedValidatorsLimitInput[] memory) {
        return abi.decode(_evmScriptCallData, (VettedValidatorsLimitInput[]));
    }

    function _validateInputData(VettedValidatorsLimitInput[] memory _decodedCallData) private view {
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

            (
                bool active,
                /* string memory name */,
                /* address rewardAddress */,
                /* uint64 stakingLimit */,
                /* uint64 stoppedValidators */,
                uint64 totalSigningKeys,
                /* uint64 usedSigningKeys */
            ) = nodeOperatorsRegistry.getNodeOperator(
                _decodedCallData[i].nodeOperatorId,
                false
            );

            require(
                totalSigningKeys >= _decodedCallData[i].stakingLimit,
                ERROR_NOT_ENOUGH_SIGNING_KEYS
            );

            require(
                active == true,
                ERROR_NODE_OPERATOR_IS_NOT_ACTIVE
            );
        }
    }
}
