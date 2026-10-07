// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import {
    IConsolidationMigrator,
    IStakingRouter,
    INodeOperatorsRegistry,
    IBaseModule,
    IMetaRegistry,
    NodeOperatorManagementProperties
} from "../../interfaces/External.sol";
import { IAllowConsolidationPair } from "../../interfaces/Factories.sol";

/// @notice Deployed `AllowConsolidationPair` (deployed-sr-<chain>.json): a motion allowlists a
///         consolidation from a source (legacy NOR) operator to a target (curated v2) operator.
contract AllowConsolidationPairScenario is EasyTrackScenarioBase {
    IAllowConsolidationPair internal factory;
    IConsolidationMigrator internal migrator;
    INodeOperatorsRegistry internal sourceModule;
    IBaseModule internal targetModule;
    IMetaRegistry internal metaRegistry;
    uint256 internal sourceModuleId;

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        factory = IAllowConsolidationPair(_factoryAddress(cfg.srArtifact, "AllowConsolidationPair"));
        migrator = IConsolidationMigrator(factory.consolidationMigrator());
        IStakingRouter router = IStakingRouter(factory.stakingRouter());
        sourceModuleId = factory.sourceModuleId();
        sourceModule = INodeOperatorsRegistry(router.getStakingModule(sourceModuleId).stakingModuleAddress);
        targetModule = IBaseModule(router.getStakingModule(factory.targetModuleId()).stakingModuleAddress);
        metaRegistry = IMetaRegistry(targetModule.META_REGISTRY());
        subject = address(factory);
        // NOTE: `creator` is set to the source operator's reward address in the fixture below.
    }

    function test_allowsConsolidationPair() external onlyForked {
        (uint256 sourceOperatorId, uint256 targetOperatorId) = _givenLinkedConsolidationPair();

        enact(_encodePair(sourceOperatorId, targetOperatorId, creator));

        assertTrue(migrator.isPairAllowed(sourceOperatorId, targetOperatorId), "consolidation pair not allowed");
    }

    /// @notice Re-allowing an already-allowed pair with a different submitter updates the stored submitter.
    function test_updatesSubmitter() external onlyForked {
        (uint256 sourceOperatorId, uint256 targetOperatorId) = _givenLinkedConsolidationPair();

        address submitterA = makeAddr("submitter-a");
        enact(_encodePair(sourceOperatorId, targetOperatorId, submitterA));
        assertEq(migrator.getSubmitter(sourceOperatorId, targetOperatorId), submitterA, "submitter A not set");

        address submitterB = makeAddr("submitter-b");
        enact(_encodePair(sourceOperatorId, targetOperatorId, submitterB));
        assertEq(migrator.getSubmitter(sourceOperatorId, targetOperatorId), submitterB, "submitter not updated");
        assertTrue(migrator.isPairAllowed(sourceOperatorId, targetOperatorId), "pair no longer allowed");
    }

    // --- scenario helpers ---

    /// @dev Build a valid pair: a fresh curated target operator and a fresh legacy-NOR source
    ///      operator, joined in a new MetaRegistry group (source as external, target as sub). Sets
    ///      `creator` to the source operator's reward address (required by factory validation).
    function _givenLinkedConsolidationPair() private returns (uint256 sourceOperatorId, uint256 targetOperatorId) {
        _grantRole(address(targetModule), "CREATE_NODE_OPERATOR_ROLE", address(this));
        address targetAddr = makeAddr("consolidation-target");
        targetOperatorId =
            targetModule.createNodeOperator(targetAddr, NodeOperatorManagementProperties(targetAddr, targetAddr, false), address(0));

        creator = makeAddr("consolidation-source-reward");
        vm.prank(cfg.agent);
        sourceOperatorId = sourceModule.addNodeOperator("scenario-source", creator);

        _grantRole(address(metaRegistry), "MANAGE_OPERATOR_GROUPS_ROLE", address(this));
        IMetaRegistry.SubNodeOperator[] memory subs = new IMetaRegistry.SubNodeOperator[](1);
        subs[0] = IMetaRegistry.SubNodeOperator({ nodeOperatorId: uint64(targetOperatorId), share: 10000 });
        IMetaRegistry.ExternalOperator[] memory exts = new IMetaRegistry.ExternalOperator[](1);
        exts[0] = IMetaRegistry.ExternalOperator({
            data: abi.encodePacked(bytes1(0), uint8(sourceModuleId), uint64(sourceOperatorId))
        });
        metaRegistry.createOrUpdateOperatorGroup(
            metaRegistry.NO_GROUP_ID(), IMetaRegistry.OperatorGroup("consolidation-group", subs, exts)
        );
    }

    function _encodePair(uint256 sourceOperatorId, uint256 targetOperatorId, address submitter)
        private
        pure
        returns (bytes memory)
    {
        uint256[] memory targets = new uint256[](1);
        targets[0] = targetOperatorId;
        // input = (address submitter, uint256 sourceOperatorId, uint256[] targetOperatorIds)
        return abi.encode(submitter, sourceOperatorId, targets);
    }
}
