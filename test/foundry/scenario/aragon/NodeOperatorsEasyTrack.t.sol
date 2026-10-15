// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {
    ILidoLocator,
    INodeOperatorsRegistry,
    IStakingRouter
} from "test/foundry/interfaces/External.sol";

/// @notice A fresh Easy Track over the live curated registry with
///         `IncreaseNodeOperatorStakingLimit` registered and handed to Voting. Two DAO votes
///         let the executor set staking limits and the Agent add an operator, then the operator
///         adds keys and raises its own limit by a motion.
contract NodeOperatorsEasyTrackTest is EasyTrackScenarioBase {
    uint256 private constant CURATED_MODULE_ID = 1;
    string private constant NODE_OPERATOR_NAME = "test_node_operator";
    uint64 private constant NEW_STAKING_LIMIT = 3;

    address internal nodeOperator = makeAddr("nodeOperator");
    address internal increaseNodeOperatorStakingLimit;

    INodeOperatorsRegistry internal registry;

    function setUp() public {
        _forkAndInitialize();

        IStakingRouter stakingRouter = IStakingRouter(ILidoLocator(config.locator).stakingRouter());
        registry = INodeOperatorsRegistry(
            stakingRouter.getStakingModule(CURATED_MODULE_ID).stakingModuleAddress
        );

        vm.label(address(registry), "NodeOperatorsRegistry");

        _deployEasyTrack(address(this));

        increaseNodeOperatorStakingLimit =
            _deployArtifact("IncreaseNodeOperatorStakingLimit", abi.encode(registry));
        easyTrack.addEVMScriptFactory(
            increaseNodeOperatorStakingLimit,
            abi.encodePacked(registry, INodeOperatorsRegistry.setNodeOperatorStakingLimit.selector)
        );

        address[] memory factories = easyTrack.getEVMScriptFactories();
        assertEq(factories.length, 1, "setup: factories");
        assertEq(factories[0], increaseNodeOperatorStakingLimit, "setup: factory");

        _handAdminToVoting();
    }

    // python: test_node_operators_easy_track_happy_path
    function testFork_IncreasesNodeOperatorStakingLimit() external {
        // The vote "Grant SET_NODE_OPERATOR_LIMIT_ROLE permission to EVMScriptExecutor"
        _grantPermission(
            evmScriptExecutor, address(registry), registry.SET_NODE_OPERATOR_LIMIT_ROLE()
        );

        // The vote "Add node operator to registry": the Agent may manage operators and adds one
        _grantPermission(config.agent, address(registry), registry.MANAGE_NODE_OPERATOR_ROLE());

        vm.prank(config.agent);
        uint256 nodeOperatorId = registry.addNodeOperator(NODE_OPERATOR_NAME, nodeOperator);

        assertEq(nodeOperatorId, registry.getNodeOperatorsCount() - 1, "node operator id");
        _assertNodeOperator(nodeOperatorId, 0, 0);

        vm.prank(nodeOperator);
        registry.addSigningKeysOperatorBH(
            nodeOperatorId, SIGNING_KEYS_COUNT, SIGNING_KEYS_PUBKEYS, SIGNING_KEYS_SIGNATURES
        );

        _assertNodeOperator(nodeOperatorId, 0, SIGNING_KEYS_COUNT);

        bytes memory callData = abi.encode(nodeOperatorId, uint256(NEW_STAKING_LIMIT));

        uint256 motionId = _createMotion(increaseNodeOperatorStakingLimit, nodeOperator, callData);

        assertEq(easyTrack.getMotions().length, 1, "motions after creation");

        _enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");
        _assertNodeOperator(nodeOperatorId, NEW_STAKING_LIMIT, SIGNING_KEYS_COUNT);
    }

    /// @dev The operator is active, named and addressed as added, holds `totalSigningKeys` keys
    ///      none of which is deposited, and has `stakingLimit` vetted
    function _assertNodeOperator(
        uint256 nodeOperatorId,
        uint64 stakingLimit,
        uint256 totalSigningKeys
    ) private view {
        (
            bool active,
            string memory name,
            address rewardAddress,
            uint64 totalVettedValidators,,
            uint64 totalAddedValidators,
            uint64 totalDepositedValidators
        ) = registry.getNodeOperator(nodeOperatorId, true);

        assertTrue(active, "active");
        assertEq(name, NODE_OPERATOR_NAME, "name");
        assertEq(rewardAddress, nodeOperator, "rewardAddress");
        assertEq(totalVettedValidators, stakingLimit, "stakingLimit");
        assertEq(totalAddedValidators, totalSigningKeys, "totalSigningKeys");
        assertEq(totalDepositedValidators, 0, "usedSigningKeys");
    }
}
