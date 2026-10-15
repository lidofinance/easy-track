// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IStakingRouter} from "test/foundry/interfaces/External.sol";
import {IUpdateStakingModuleShareLimits} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `UpdateStakingModuleShareLimits:CSM` of `deployed-sr-<chain>.json`: a
///         motion updates the module's stake share limit & priority exit share threshold on the
///         Staking Router
contract UpdateStakingModuleShareLimitsTest is EasyTrackScenarioBase {
    /// @dev The Staking Router expresses shares in basis points
    uint16 internal constant MAX_BP = 10000;

    /// @dev How far a planned motion moves each share, capped by the factory's per-motion deltas
    uint16 internal constant SHARE_STEP = 100;

    /// @dev A second factory, bound to a module id the Staking Router has never registered
    uint256 internal constant MISSING_MODULE_ID = 999;
    string internal constant MISSING_MODULE_FACTORY_NAME = "CSM v3-MISSING";
    uint16 internal constant MAX_STAKE_SHARE_LIMIT_INCREASE = 500;
    uint16 internal constant MAX_STAKE_SHARE_LIMIT_DECREASE = 400;
    uint16 internal constant MAX_PRIORITY_EXIT_SHARE_THRESHOLD_INCREASE = 300;
    uint16 internal constant MAX_PRIORITY_EXIT_SHARE_THRESHOLD_DECREASE = 200;
    uint16 internal constant MISSING_MODULE_NEW_SHARE = 100;

    IUpdateStakingModuleShareLimits internal factory;
    IStakingRouter internal stakingRouter;
    uint256 internal stakingModuleId;

    function setUp() public {
        _forkAndInitialize();

        factory = IUpdateStakingModuleShareLimits(
            _factoryAddress(config.srArtifact, "UpdateStakingModuleShareLimits:CSM")
        );
        stakingRouter = IStakingRouter(factory.stakingRouter());
        stakingModuleId = factory.stakingModuleId();

        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
    }

    // python: test_update_staking_module_share_limits_via_motion_scenario, the raising branch
    function testFork_IncreasesModuleShareLimits() external {
        (uint16 newStakeShareLimit, uint16 newPriorityExitShareThreshold, bytes memory callData) =
            _plannedIncrease();

        _enact(callData);

        _assertModuleShares(newStakeShareLimit, newPriorityExitShareThreshold);
    }

    // python: test_update_staking_module_share_limits_via_motion_scenario, the lowering branch
    function testFork_DecreasesModuleShareLimits() external {
        (uint16 newStakeShareLimit, uint16 newPriorityExitShareThreshold, bytes memory callData) =
            _plannedDecrease();

        _enact(callData);

        _assertModuleShares(newStakeShareLimit, newPriorityExitShareThreshold);
    }

    // python: test_update_staking_module_share_limits_reverts_for_missing_module
    function testFork_RevertWhen_ModuleIsNotRegistered() external {
        address missingModuleFactory = _deployArtifact(
            "UpdateStakingModuleShareLimits",
            abi.encode(
                creator,
                MISSING_MODULE_FACTORY_NAME,
                address(stakingRouter),
                MISSING_MODULE_ID,
                MAX_STAKE_SHARE_LIMIT_INCREASE,
                MAX_STAKE_SHARE_LIMIT_DECREASE,
                MAX_PRIORITY_EXIT_SHARE_THRESHOLD_INCREASE,
                MAX_PRIORITY_EXIT_SHARE_THRESHOLD_DECREASE
            )
        );
        _registerFactory(
            missingModuleFactory,
            abi.encodePacked(
                missingModuleFactory,
                IUpdateStakingModuleShareLimits.validateParams.selector,
                address(stakingRouter),
                IStakingRouter.updateModuleShares.selector
            )
        );
        bytes memory callData =
            abi.encode(uint16(0), MISSING_MODULE_NEW_SHARE, uint16(0), MISSING_MODULE_NEW_SHARE);

        // The router's custom error, which the Brownie suite sees rendered as a string
        vm.prank(creator);
        vm.expectRevert(IStakingRouter.StakingModuleUnregistered.selector);
        easyTrack.createMotion(missingModuleFactory, callData);
    }

    // python: test_update_staking_module_share_limits_reverts_on_enactment_if_current_values_changed
    function testFork_RevertWhen_CurrentSharesChangeBeforeEnact() external {
        (uint16 stakeShareLimit, uint16 priorityExitShareThreshold) = _currentShares();
        // the planned motion commits the current shares
        (,, bytes memory callData) = _plannedIncrease();
        uint256 motionId = _createMotion(callData);

        // Move the module's shares so the committed current values no longer match
        vm.prank(evmScriptExecutor);
        stakingRouter.updateModuleShares(
            stakingModuleId, stakeShareLimit + 1, priorityExitShareThreshold + 1
        );

        _passMotionDuration();

        vm.prank(stranger);
        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        easyTrack.enactMotion(motionId, callData);
    }

    function _assertModuleShares(uint16 stakeShareLimit, uint16 priorityExitShareThreshold)
        private
        view
    {
        IStakingRouter.StakingModule memory stakingModule =
            stakingRouter.getStakingModule(stakingModuleId);

        assertEq(stakingModule.stakeShareLimit, stakeShareLimit, "stakeShareLimit");
        assertEq(
            stakingModule.priorityExitShareThreshold,
            priorityExitShareThreshold,
            "priorityExitShareThreshold"
        );
    }

    /// @dev Raise the threshold, the upper bound of the stake share, then the stake share, each
    ///      by at most the factory's per-motion delta, keeping `newStake <= newThreshold <= MAX_BP`
    function _plannedIncrease()
        private
        view
        returns (
            uint16 newStakeShareLimit,
            uint16 newPriorityExitShareThreshold,
            bytes memory callData
        )
    {
        (uint16 stakeShareLimit, uint16 priorityExitShareThreshold) = _currentShares();

        newPriorityExitShareThreshold = priorityExitShareThreshold
            + _min(SHARE_STEP, factory.maxPriorityExitShareThresholdIncrease());
        assertLe(newPriorityExitShareThreshold, MAX_BP, "setup: room to raise the threshold");
        assertGt(
            newPriorityExitShareThreshold,
            priorityExitShareThreshold,
            "setup: room to raise the threshold"
        );

        newStakeShareLimit =
            stakeShareLimit + _min(SHARE_STEP, factory.maxStakeShareLimitIncrease());
        assertLe(
            newStakeShareLimit,
            newPriorityExitShareThreshold,
            "setup: room to raise the stake share"
        );
        assertGt(newStakeShareLimit, stakeShareLimit, "setup: room to raise the stake share");

        callData = abi.encode(
            stakeShareLimit,
            newStakeShareLimit,
            priorityExitShareThreshold,
            newPriorityExitShareThreshold
        );
    }

    /// @dev Lower the stake share, then the threshold, each by at most the factory's per-motion
    ///      delta, keeping `newStake <= newThreshold`
    function _plannedDecrease()
        private
        view
        returns (
            uint16 newStakeShareLimit,
            uint16 newPriorityExitShareThreshold,
            bytes memory callData
        )
    {
        (uint16 stakeShareLimit, uint16 priorityExitShareThreshold) = _currentShares();

        newStakeShareLimit = stakeShareLimit
            - _min(_min(SHARE_STEP, factory.maxStakeShareLimitDecrease()), stakeShareLimit);
        newPriorityExitShareThreshold = priorityExitShareThreshold
            - _min(
                _min(SHARE_STEP, factory.maxPriorityExitShareThresholdDecrease()),
                priorityExitShareThreshold - newStakeShareLimit
            );
        assertLt(newStakeShareLimit, stakeShareLimit, "setup: room to lower the stake share");
        assertLt(
            newPriorityExitShareThreshold,
            priorityExitShareThreshold,
            "setup: room to lower the threshold"
        );

        callData = abi.encode(
            stakeShareLimit,
            newStakeShareLimit,
            priorityExitShareThreshold,
            newPriorityExitShareThreshold
        );
    }

    function _currentShares()
        private
        view
        returns (uint16 stakeShareLimit, uint16 priorityExitShareThreshold)
    {
        IStakingRouter.StakingModule memory stakingModule =
            stakingRouter.getStakingModule(stakingModuleId);

        return (stakingModule.stakeShareLimit, stakingModule.priorityExitShareThreshold);
    }

    function _min(uint16 a, uint16 b) private pure returns (uint16) {
        return a < b ? a : b;
    }
}
