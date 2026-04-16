// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/ICuratedModule.sol";
import "../interfaces/IConsolidationMigrator.sol";
import "../interfaces/IMetaRegistry.sol";
import "../interfaces/IStakingRouter.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to allow consolidation between a curated node operator and a target module operator
contract AllowConsolidationPair is IEVMScriptFactory {
    struct AllowConsolidationPairInput {
        address submitter;
        uint256 sourceOperatorId;
        uint256[] targetOperatorIds;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_SOURCE_OPERATOR_ID_DOES_NOT_EXIST = "SOURCE_OPERATOR_ID_DOES_NOT_EXIST";
    string private constant ERROR_EMPTY_TARGET_OPERATOR_IDS = "EMPTY_TARGET_OPERATOR_IDS";
    string private constant ERROR_DUPLICATE_TARGET_OPERATOR_ID = "DUPLICATE_TARGET_OPERATOR_ID";
    string private constant ERROR_NODE_OPERATOR_IS_NOT_ACTIVE = "NODE_OPERATOR_IS_NOT_ACTIVE";
    string private constant ERROR_OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY =
        "OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY";
    string private constant ERROR_CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER =
        "CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER";
    string private constant ERROR_ZERO_MIGRATOR = "ZERO_MIGRATOR";
    string private constant ERROR_ZERO_SUBMITTER = "ZERO_SUBMITTER";

    /// @notice keccak256("MANAGE_SIGNING_KEYS")
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE =
        0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee;

    // -------------
    // CONSTANTS
    // -------------

    // ExternalOperatorLib.OperatorType.NOR
    uint8 private constant EXT_OPERATOR_TYPE_NOR = 0;
    // MetaRegistry.NO_GROUP_ID
    uint256 private constant NO_GROUP_ID = 0;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Consolidation migrator contract that maintains the allowlist.
    IConsolidationMigrator public immutable consolidationMigrator;
    /// @notice StakingRouter used to get module addresses for the source and target module ids.
    IStakingRouter public immutable stakingRouter;
    /// @notice Cached source module id that must equal the migrator binding.
    uint256 public immutable sourceModuleId;
    /// @notice Cached target module id that must equal the migrator binding.
    uint256 public immutable targetModuleId;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _consolidationMigrator) {
        require(_consolidationMigrator != address(0), ERROR_ZERO_MIGRATOR);

        IConsolidationMigrator migrator = IConsolidationMigrator(_consolidationMigrator);

        stakingRouter = IStakingRouter(migrator.getStakingRouter());
        sourceModuleId = migrator.sourceModuleId();
        targetModuleId = migrator.targetModuleId();
        
        consolidationMigrator = migrator;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript that allows consolidation between the curated and the target operators.
    /// @param _creator address who creates EVMScript
    /// @param _evmScriptCallData Encoded AllowConsolidationPairInput
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override returns (bytes memory) {
        AllowConsolidationPairInput memory input = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_creator, input);

        uint256 targetsCount = input.targetOperatorIds.length;
        bytes[] memory encodedCalldata = new bytes[](targetsCount);
        for (uint256 i; i < targetsCount; ++i) {
            encodedCalldata[i] = abi.encode(
                input.sourceOperatorId,
                input.targetOperatorIds[i],
                input.submitter
            );
        }

        return
            EVMScriptCreator.createEVMScript(
                address(consolidationMigrator),
                IConsolidationMigrator.allowPair.selector,
                encodedCalldata
            );
    }

    /// @notice Decodes call data used by createEVMScript method.
    /// @param _evmScriptCallData Encoded AllowConsolidationPairInput
    /// @return AllowConsolidationPairInput struct with the decoded inputs
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (AllowConsolidationPairInput memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (AllowConsolidationPairInput memory) {
        (
            address submitter,
            uint256 sourceOperatorId,
            uint256[] memory targetOperatorIds
        ) = abi.decode(_evmScriptCallData, (address, uint256, uint256[]));

        return AllowConsolidationPairInput({
            submitter: submitter,
            sourceOperatorId: sourceOperatorId,
            targetOperatorIds: targetOperatorIds
        });
    }

    function _validateInputData(
        address creator,
        AllowConsolidationPairInput memory input
    ) private view {
        require(input.submitter != address(0), ERROR_ZERO_SUBMITTER);

        INodeOperatorsRegistry sourceModule = INodeOperatorsRegistry(stakingRouter.getStakingModule(sourceModuleId).stakingModuleAddress);

        uint256 sourceCount = sourceModule.getNodeOperatorsCount();
        require(input.sourceOperatorId < sourceCount, ERROR_SOURCE_OPERATOR_ID_DOES_NOT_EXIST);

        (bool active, , address rewardAddress, , , , ) = sourceModule.getNodeOperator(
            input.sourceOperatorId,
            false
        );
        require(active, ERROR_NODE_OPERATOR_IS_NOT_ACTIVE);

        uint256[] memory roleParams = new uint256[](1);
        roleParams[0] = input.sourceOperatorId;
        require(
            creator == rewardAddress ||
                sourceModule.canPerform(creator, MANAGE_SIGNING_KEYS_ROLE, roleParams),
            ERROR_CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER
        );

        _validateOperatorIds(input.sourceOperatorId, input.targetOperatorIds);
    }

    function _validateOperatorIds(
        uint256 sourceOperatorId,
        uint256[] memory targetOperatorIds
    ) private view {
        ICuratedModule targetModule = ICuratedModule(stakingRouter.getStakingModule(targetModuleId).stakingModuleAddress);
        IMetaRegistry metaRegistry = targetModule.META_REGISTRY();

        uint256 sourceGroupId = metaRegistry.getExternalOperatorGroupId(
            IMetaRegistry.ExternalOperator({
                data: abi.encodePacked(
                    bytes1(EXT_OPERATOR_TYPE_NOR),
                    uint8(sourceModuleId),
                    uint64(sourceOperatorId)
                )
            })
        );
        require(
            sourceGroupId != NO_GROUP_ID,
            ERROR_OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY
        );

        uint256 targetsCount = targetOperatorIds.length;
        require(targetsCount > 0, ERROR_EMPTY_TARGET_OPERATOR_IDS);

        for (uint256 i; i < targetsCount; ++i) {
            uint256 targetOperatorId = targetOperatorIds[i];

            for (uint256 j = i + 1; j < targetsCount; ++j) {
                require(
                    targetOperatorId != targetOperatorIds[j],
                    ERROR_DUPLICATE_TARGET_OPERATOR_ID
                );
            }

            require(
                targetModule.getNodeOperatorIsActive(targetOperatorId),
                ERROR_NODE_OPERATOR_IS_NOT_ACTIVE
            );

            require(
                metaRegistry.getNodeOperatorGroupId(targetOperatorId) == sourceGroupId,
                ERROR_OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY
            );
        }
    }
}
