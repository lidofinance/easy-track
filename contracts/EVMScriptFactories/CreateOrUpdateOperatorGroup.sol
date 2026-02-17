// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IMetaRegistry.sol";

/// @notice Creates EVMScript to create or update a MetaRegistry operator group.
contract CreateOrUpdateOperatorGroup is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_META_REGISTRY_IS_ZERO_ADDRESS =
        "META_REGISTRY_IS_ZERO_ADDRESS";
    string private constant ERROR_INVALID_GROUP_ID = "INVALID_GROUP_ID";
    string private constant ERROR_EMPTY_SUB_NODE_OPERATORS =
        "EMPTY_SUB_NODE_OPERATORS";
    string private constant ERROR_INVALID_EMPTY_GROUP_UPDATE =
        "INVALID_EMPTY_GROUP_UPDATE";
    string private constant ERROR_SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH =
        "SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH";
    string private constant ERROR_DUPLICATE_SUB_NODE_OPERATOR =
        "DUPLICATE_SUB_NODE_OPERATOR";
    string private constant ERROR_DUPLICATE_EXTERNAL_OPERATOR =
        "DUPLICATE_EXTERNAL_OPERATOR";

    // -------------
    // CONSTANTS
    // -------------

    uint256 private constant MAX_BP = 10000;
    // ExternalOperatorLib.OperatorType.NOR
    uint8 private constant EXT_OPERATOR_TYPE_NOR = 0;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Alias for factory (e.g. "CMv2")
    string public name;

    /// @notice Address of MetaRegistry contract
    IMetaRegistry public immutable metaRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        string memory _name,
        address _metaRegistry
    ) TrustedCaller(_trustedCaller) {
        require(
            _metaRegistry != address(0),
            ERROR_META_REGISTRY_IS_ZERO_ADDRESS
        );

        name = _name;
        metaRegistry = IMetaRegistry(_metaRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript for `MetaRegistry.createOrUpdateOperatorGroup`.
    /// @param _creator Address who creates EVMScript.
    /// @param _evmScriptCallData Encoded method arguments in format
    ///        `abi.encode(uint256 groupId, IMetaRegistry.OperatorGroup groupInfo)`.
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            uint256 groupId,
            IMetaRegistry.OperatorGroup memory groupInfo
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(groupId, groupInfo);

        return
            EVMScriptCreator.createEVMScript(
                address(metaRegistry),
                IMetaRegistry.createOrUpdateOperatorGroup.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method.
    /// @param _evmScriptCallData Encoded tuple: (uint256 groupId, IMetaRegistry.OperatorGroup groupInfo)
    /// @return groupId Group ID to update, or NO_GROUP_ID to create.
    /// @return groupInfo Group definition.
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (uint256 groupId, IMetaRegistry.OperatorGroup memory groupInfo)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    /// @notice Encodes `ExternalOperator.data` for a NOR external operator.
    /// @dev Format:
    /// `[operatorType:1 byte][moduleId:1 byte][nodeOperatorId:8 bytes]`.
    function encodeNORExtOperatorData(uint8 moduleId, uint64 nodeOperatorId)
        external
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(
            bytes1(EXT_OPERATOR_TYPE_NOR),
            moduleId,
            nodeOperatorId
        );
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (uint256 groupId, IMetaRegistry.OperatorGroup memory groupInfo)
    {
        return abi.decode(_evmScriptCallData, (uint256, IMetaRegistry.OperatorGroup));
    }

    function _validateInputData(
        uint256 groupId,
        IMetaRegistry.OperatorGroup memory groupInfo
    ) private view {
        uint256 noGroupId = metaRegistry.NO_GROUP_ID();
        uint256 groupsCount = metaRegistry.getOperatorGroupsCount();
        bool isCreate = groupId == noGroupId;
        uint256 subNodeOperatorsCount = groupInfo.subNodeOperators.length;
        uint256 externalOperatorsCount = groupInfo.externalOperators.length;
        bool hasSubNodeOperators = subNodeOperatorsCount > 0;
        bool hasExternalOperators = externalOperatorsCount > 0;
        bool isClearUpdate = !hasSubNodeOperators && !hasExternalOperators;

        if (isCreate) {
            require(!isClearUpdate, ERROR_EMPTY_SUB_NODE_OPERATORS);
        } else {
            require(groupId < groupsCount, ERROR_INVALID_GROUP_ID);
        }

        if (!isCreate && isClearUpdate) {
            return;
        }

        require(hasSubNodeOperators, ERROR_INVALID_EMPTY_GROUP_UPDATE);

        uint256 sharesSum;

        for (uint256 i = 0; i < subNodeOperatorsCount; ++i) {
            uint64 nodeOperatorId = groupInfo.subNodeOperators[i].nodeOperatorId;
            sharesSum += groupInfo.subNodeOperators[i].share;

            for (uint256 j = i + 1; j < subNodeOperatorsCount; ++j) {
                require(
                    nodeOperatorId != groupInfo.subNodeOperators[j].nodeOperatorId,
                    ERROR_DUPLICATE_SUB_NODE_OPERATOR
                );
            }
        }

        require(
            sharesSum == MAX_BP,
            ERROR_SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH
        );

        for (uint256 i = 0; i < externalOperatorsCount; ++i) {
            bytes32 externalOperatorHash = keccak256(
                groupInfo.externalOperators[i].data
            );
            for (uint256 j = i + 1; j < externalOperatorsCount; ++j) {
                require(
                    externalOperatorHash !=
                        keccak256(groupInfo.externalOperators[j].data),
                    ERROR_DUPLICATE_EXTERNAL_OPERATOR
                );
            }
        }
    }
}
