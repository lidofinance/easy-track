// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/ICuratedModule.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IMetaRegistry.sol";
import "../interfaces/IStakingRouter.sol";

/// @notice Creates EVMScript to create or update a MetaRegistry operator group.
contract CreateOrUpdateOperatorGroup is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_META_REGISTRY_IS_ZERO_ADDRESS =
        "META_REGISTRY_IS_ZERO_ADDRESS";
    string private constant ERROR_INVALID_GROUP_ID = "INVALID_GROUP_ID";
    string private constant ERROR_EMPTY_GROUP = "EMPTY_GROUP";
    string private constant ERROR_INVALID_EMPTY_GROUP_UPDATE =
        "INVALID_EMPTY_GROUP_UPDATE";
    string private constant ERROR_SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH =
        "SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH";
    string private constant ERROR_DUPLICATE_SUB_NODE_OPERATOR =
        "DUPLICATE_SUB_NODE_OPERATOR";
    string private constant ERROR_DUPLICATE_EXTERNAL_OPERATOR =
        "DUPLICATE_EXTERNAL_OPERATOR";
    string private constant ERROR_SUB_NODE_OPERATOR_DOES_NOT_EXIST =
        "SUB_NODE_OPERATOR_DOES_NOT_EXIST";
    string private constant ERROR_INVALID_EXTERNAL_OPERATOR_DATA_LENGTH =
        "INVALID_EXTERNAL_OPERATOR_DATA_LENGTH";
    string private constant ERROR_UNSUPPORTED_EXTERNAL_OPERATOR_TYPE =
        "UNSUPPORTED_EXTERNAL_OPERATOR_TYPE";
    string private constant ERROR_EXTERNAL_OPERATOR_MODULE_DOES_NOT_EXIST =
        "EXTERNAL_OPERATOR_MODULE_DOES_NOT_EXIST";
    string private constant ERROR_EXTERNAL_OPERATOR_DOES_NOT_EXIST =
        "EXTERNAL_OPERATOR_DOES_NOT_EXIST";

    // -------------
    // CONSTANTS
    // -------------

    uint256 private constant MAX_BP = 10000;
    // ExternalOperatorLib.OperatorType.NOR
    uint8 private constant EXT_OPERATOR_TYPE_NOR = 0;
    uint256 private constant EXT_OPERATOR_DATA_LENGTH = 10;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Alias for factory (e.g. "CMv2")
    string public name;

    /// @notice Address of MetaRegistry contract
    IMetaRegistry public immutable metaRegistry;
    /// @notice Curated module taken from MetaRegistry at deployment time
    ICuratedModule public immutable module;
    /// @notice Staking router taken from MetaRegistry at deployment time
    IStakingRouter public immutable stakingRouter;

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

        IMetaRegistry registry = IMetaRegistry(_metaRegistry);
        metaRegistry = registry;
        // Snapshot dependencies at deploy time.
        // If MetaRegistry changes MODULE/STAKING_ROUTER, this factory must be redeployed.
        module = ICuratedModule(registry.MODULE());
        stakingRouter = IStakingRouter(registry.STAKING_ROUTER());

        name = _name;
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

    /// @notice Decodes `ExternalOperator.data` for a NOR external operator.
    /// @dev Expected format:
    /// `[operatorType:1 byte][moduleId:1 byte][nodeOperatorId:8 bytes]`.
    function decodeNORExtOperatorData(bytes memory _externalOperatorData)
        external
        pure
        returns (uint8 moduleId, uint64 nodeOperatorId)
    {
        return _decodeNORExtOperatorData(_externalOperatorData);
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
        uint256 subNodeOperatorsCount = groupInfo.subNodeOperators.length;
        uint256 externalOperatorsCount = groupInfo.externalOperators.length;

        require(
            groupId < metaRegistry.getOperatorGroupsCount(),
            ERROR_INVALID_GROUP_ID
        );

        if (groupId == metaRegistry.NO_GROUP_ID()) {
            require(subNodeOperatorsCount > 0, ERROR_EMPTY_GROUP);
        } else if (subNodeOperatorsCount == 0) {
            require(
                externalOperatorsCount == 0,
                ERROR_INVALID_EMPTY_GROUP_UPDATE
            );
            return;
        }

        _validateSubNodeOperators(groupInfo.subNodeOperators);
        _validateExternalOperators(groupInfo.externalOperators);
    }

    function _validateSubNodeOperators(
        IMetaRegistry.SubNodeOperator[] memory _subNodeOperators
    ) private view {
        uint256 moduleNodeOperatorsCount = module.getNodeOperatorsCount();
        uint256 subNodeOperatorsCount = _subNodeOperators.length;

        uint256 sharesSum;
        for (uint256 i = 0; i < subNodeOperatorsCount; ++i) {
            uint64 nodeOperatorId = _subNodeOperators[i].nodeOperatorId;
            require(
                nodeOperatorId < moduleNodeOperatorsCount,
                ERROR_SUB_NODE_OPERATOR_DOES_NOT_EXIST
            );
            sharesSum += _subNodeOperators[i].share;

            for (uint256 j = i + 1; j < subNodeOperatorsCount; ++j) {
                require(
                    nodeOperatorId != _subNodeOperators[j].nodeOperatorId,
                    ERROR_DUPLICATE_SUB_NODE_OPERATOR
                );
            }
        }

        require(
            sharesSum == MAX_BP,
            ERROR_SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH
        );
    }

    function _validateExternalOperators(
        IMetaRegistry.ExternalOperator[] memory _externalOperators
    ) private view {
        uint256 externalOperatorsCount = _externalOperators.length;
        for (uint256 i = 0; i < externalOperatorsCount; ++i) {
            (
                uint8 externalModuleId,
                uint64 externalNodeOperatorId
            ) = _decodeNORExtOperatorData(_externalOperators[i].data);

            INodeOperatorsRegistry externalModule = INodeOperatorsRegistry(
                stakingRouter.getStakingModule(externalModuleId).stakingModuleAddress
            );
            require(
                externalNodeOperatorId < externalModule.getNodeOperatorsCount(),
                ERROR_EXTERNAL_OPERATOR_DOES_NOT_EXIST
            );

            bytes32 externalOperatorHash = keccak256(
                _externalOperators[i].data
            );
            for (uint256 j = i + 1; j < externalOperatorsCount; ++j) {
                require(
                    externalOperatorHash !=
                        keccak256(_externalOperators[j].data),
                    ERROR_DUPLICATE_EXTERNAL_OPERATOR
                );
            }
        }
    }

    function _decodeNORExtOperatorData(bytes memory _externalOperatorData)
        private
        pure
        returns (uint8 moduleId, uint64 nodeOperatorId)
    {
        require(
            _externalOperatorData.length == EXT_OPERATOR_DATA_LENGTH,
            ERROR_INVALID_EXTERNAL_OPERATOR_DATA_LENGTH
        );
        require(
            uint8(_externalOperatorData[0]) == EXT_OPERATOR_TYPE_NOR,
            ERROR_UNSUPPORTED_EXTERNAL_OPERATOR_TYPE
        );

        moduleId = _moduleIdNOR(_externalOperatorData);
        nodeOperatorId = _nodeOperatorIdNOR(_externalOperatorData);
    }

    function _moduleIdNOR(bytes memory _externalOperatorData)
        private
        pure
        returns (uint8)
    {
        return uint8(_externalOperatorData[1]);
    }

    function _nodeOperatorIdNOR(bytes memory _externalOperatorData)
        private
        pure
        returns (uint64 ret)
    {
        assembly {
            // bytes layout in memory: [length (32 bytes)][data...]
            // data[2..9] starts at (_externalOperatorData + 34).
            // Keep the top 8 bytes as uint64.
            ret := shr(192, mload(add(_externalOperatorData, 34)))
        }
    }
}
