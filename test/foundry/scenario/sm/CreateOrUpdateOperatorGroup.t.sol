// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import {
    IMetaRegistry,
    IBaseModule,
    IStakingRouter,
    INodeOperatorsRegistry,
    NodeOperatorManagementProperties
} from "../../interfaces/External.sol";
import { ICreateOrUpdateOperatorGroup } from "../../interfaces/Factories.sol";

/// @notice Deployed `CreateOrUpdateOperatorGroup:CM` (deployed-sm-<chain>.json): a motion creates a
///         new MetaRegistry operator group with a sub node operator and an external operator.
contract CreateOrUpdateOperatorGroupScenario is EasyTrackScenarioBase {
    ICreateOrUpdateOperatorGroup internal factory;
    IMetaRegistry internal metaRegistry;
    IBaseModule internal module;
    INodeOperatorsRegistry internal externalModule;
    uint256 internal externalModuleId;

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        factory = ICreateOrUpdateOperatorGroup(_factoryAddress(cfg.smArtifact, "CreateOrUpdateOperatorGroup:CM"));
        metaRegistry = IMetaRegistry(factory.metaRegistry());
        module = IBaseModule(factory.module());
        IStakingRouter router = IStakingRouter(factory.stakingRouter());
        externalModuleId = factory.allowedExternalModuleId();
        externalModule = INodeOperatorsRegistry(router.getStakingModule(externalModuleId).stakingModuleAddress);
        subject = address(factory);
        creator = factory.trustedCaller();
    }

    function test_createsOperatorGroup() external onlyForked {
        (uint64 subOperator, uint64 externalOperator) = _givenGroupMembers();
        uint256 groupsBefore = metaRegistry.getOperatorGroupsCount();

        enact(_encodeNewGroup(subOperator, externalOperator));

        uint256 newGroupId = metaRegistry.getOperatorGroupsCount();
        assertEq(newGroupId, groupsBefore + 1, "operator group not created");
        // both members now resolve to the new group
        assertEq(metaRegistry.getNodeOperatorGroupId(subOperator), newGroupId, "sub operator not in group");
        assertEq(_externalOperatorGroupId(externalOperator), newGroupId, "external operator not in group");
    }

    // --- scenario helpers ---

    /// @dev A fresh curated (sub) operator and a fresh legacy-NOR (external) operator.
    function _givenGroupMembers() private returns (uint64 subOperator, uint64 externalOperator) {
        _grantRole(address(module), "CREATE_NODE_OPERATOR_ROLE", address(this));
        address subAddr = makeAddr("cm-sub-operator");
        subOperator =
            uint64(module.createNodeOperator(subAddr, NodeOperatorManagementProperties(subAddr, subAddr, false), address(0)));

        vm.prank(cfg.agent);
        externalOperator = uint64(externalModule.addNodeOperator("scenario-external", makeAddr("nor-external-reward")));
    }

    function _encodeNewGroup(uint64 subOperator, uint64 externalOperator) private view returns (bytes memory) {
        IMetaRegistry.SubNodeOperator[] memory subs = new IMetaRegistry.SubNodeOperator[](1);
        subs[0] = IMetaRegistry.SubNodeOperator({ nodeOperatorId: subOperator, share: 10000 });

        IMetaRegistry.ExternalOperator[] memory exts = new IMetaRegistry.ExternalOperator[](1);
        exts[0] = IMetaRegistry.ExternalOperator({
            data: abi.encodePacked(bytes1(0), uint8(externalModuleId), externalOperator)
        });

        IMetaRegistry.OperatorGroup memory newGroup =
            IMetaRegistry.OperatorGroup({ name: "scenario-group", subNodeOperators: subs, externalOperators: exts });
        IMetaRegistry.OperatorGroup memory currentEmpty;
        return abi.encode(metaRegistry.NO_GROUP_ID(), currentEmpty, newGroup);
    }

    function _externalOperatorGroupId(uint64 externalOperator) private view returns (uint256) {
        return metaRegistry.getExternalOperatorGroupId(
            IMetaRegistry.ExternalOperator({
                data: abi.encodePacked(bytes1(0), uint8(externalModuleId), externalOperator)
            })
        );
    }
}
