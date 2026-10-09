// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {
    IBaseModule,
    IConsolidationMigrator,
    IMetaRegistry,
    INodeOperatorsRegistry,
    IStakingRouter,
    NodeOperatorManagementProperties
} from "test/foundry/interfaces/External.sol";
import {IAllowConsolidationPair} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `AllowConsolidationPair` of `deployed-sr-<chain>.json`: a motion allowlists
///         a consolidation from a source operator of the legacy NOR to a target operator of the
///         curated module v2
contract AllowConsolidationPairTest is EasyTrackScenarioBase {
    address internal submitter = makeAddr("submitter");

    IConsolidationMigrator internal consolidationMigrator;
    INodeOperatorsRegistry internal sourceModule;
    IBaseModule internal targetModule;
    IMetaRegistry internal metaRegistry;
    uint256 internal sourceModuleId;

    function setUp() public {
        _forkAndInitialize();

        IAllowConsolidationPair factory =
            IAllowConsolidationPair(_factoryAddress(config.srArtifact, "AllowConsolidationPair"));
        IStakingRouter stakingRouter = IStakingRouter(factory.stakingRouter());
        consolidationMigrator = IConsolidationMigrator(factory.consolidationMigrator());
        sourceModuleId = factory.sourceModuleId();
        sourceModule = INodeOperatorsRegistry(
            stakingRouter.getStakingModule(sourceModuleId).stakingModuleAddress
        );
        targetModule = IBaseModule(
            stakingRouter.getStakingModule(factory.targetModuleId()).stakingModuleAddress
        );
        metaRegistry = IMetaRegistry(targetModule.META_REGISTRY());

        // The factory has no trusted caller: `_createLinkedConsolidationPair` sets `creator` to the
        // source operator's reward address
        evmScriptFactory = address(factory);
    }

    // python: test_allow_consolidation_pair_via_motion_scenario
    function testFork_AllowsConsolidationPair() external {
        (uint256 sourceOperatorId, uint256 targetOperatorId) = _createLinkedConsolidationPair();

        _enact(_encodePair(sourceOperatorId, targetOperatorId, submitter));

        assertTrue(
            consolidationMigrator.isPairAllowed(sourceOperatorId, targetOperatorId), "isPairAllowed"
        );
        assertEq(
            consolidationMigrator.getSubmitter(sourceOperatorId, targetOperatorId),
            submitter,
            "getSubmitter"
        );
    }

    // python: test_allow_consolidation_pair_overwrites_submitter_via_second_motion
    function testFork_UpdatesSubmitterOfAllowedPair() external {
        (uint256 sourceOperatorId, uint256 targetOperatorId) = _createLinkedConsolidationPair();
        address newSubmitter = makeAddr("newSubmitter");
        _enact(_encodePair(sourceOperatorId, targetOperatorId, submitter));

        _enact(_encodePair(sourceOperatorId, targetOperatorId, newSubmitter));

        assertEq(
            consolidationMigrator.getSubmitter(sourceOperatorId, targetOperatorId),
            newSubmitter,
            "getSubmitter"
        );
        assertTrue(
            consolidationMigrator.isPairAllowed(sourceOperatorId, targetOperatorId), "isPairAllowed"
        );
    }

    /// @dev A fresh curated target operator and a fresh legacy NOR source operator, linked in a new
    ///      MetaRegistry group: the target as its sub operator, the source as its external
    ///      operator. Sets `creator` to the source operator's reward address, which the factory
    ///      requires.
    function _createLinkedConsolidationPair()
        private
        returns (uint256 sourceOperatorId, uint256 targetOperatorId)
    {
        _grantRole(address(targetModule), CREATE_NODE_OPERATOR_ROLE, address(this));
        address targetOperator = makeAddr("consolidationTarget");
        targetOperatorId = targetModule.createNodeOperator(
            targetOperator,
            NodeOperatorManagementProperties(targetOperator, targetOperator, false),
            address(0)
        );

        creator = makeAddr("consolidationSourceReward");

        vm.prank(config.agent);
        sourceOperatorId = sourceModule.addNodeOperator("scenario-source", creator);

        _grantRole(address(metaRegistry), MANAGE_OPERATOR_GROUPS_ROLE, address(this));
        metaRegistry.createOrUpdateOperatorGroup(
            metaRegistry.NO_GROUP_ID(),
            IMetaRegistry.OperatorGroup(
                "consolidation-group",
                _subNodeOperators(uint64(targetOperatorId)),
                _externalOperators(sourceModuleId, uint64(sourceOperatorId))
            )
        );
    }

    /// @dev `AllowConsolidationPairInput`:
    ///      (address submitter, uint256 sourceOperatorId, uint256[] targetOperatorIds)
    function _encodePair(uint256 sourceOperatorId, uint256 targetOperatorId, address pairSubmitter)
        private
        pure
        returns (bytes memory)
    {
        uint256[] memory targetOperatorIds = new uint256[](1);
        targetOperatorIds[0] = targetOperatorId;

        return abi.encode(pairSubmitter, sourceOperatorId, targetOperatorIds);
    }
}
