// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import { IStakingRouter } from "../../interfaces/External.sol";
import { IUpdateStakingModuleShareLimits } from "../../interfaces/Factories.sol";

/// @notice Deployed `UpdateStakingModuleShareLimits:CSM` (deployed-sr-<chain>.json): a motion
///         updates the module's stake share limit & priority exit threshold on the Staking Router.
contract UpdateStakingModuleShareLimitsScenario is EasyTrackScenarioBase {
    IUpdateStakingModuleShareLimits internal factory;
    IStakingRouter internal router;
    uint256 internal moduleId;

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        factory = IUpdateStakingModuleShareLimits(_factoryAddress(cfg.srArtifact, "UpdateStakingModuleShareLimits:CSM"));
        router = IStakingRouter(factory.stakingRouter());
        moduleId = factory.stakingModuleId();
        subject = address(factory);
        creator = factory.trustedCaller();
    }

    function test_increasesModuleShareLimits() external onlyForked {
        (uint16 newStake, uint16 newThreshold, bytes memory callData) = _plannedIncrease();

        enact(callData);

        _assertShares(newStake, newThreshold);
    }

    function test_decreasesModuleShareLimits() external onlyForked {
        (uint16 newStake, uint16 newThreshold, bytes memory callData) = _plannedDecrease();

        enact(callData);

        _assertShares(newStake, newThreshold);
    }

    function test_revertsWhenCurrentSharesChangeBeforeEnact() external onlyForked {
        (uint16 curStake, uint16 curThreshold) = _currentShares();
        (,, bytes memory callData) = _plannedIncrease(); // commits the current values above

        vm.prank(creator);
        uint256 motionId = easyTrack.createMotion(subject, callData);

        // move the module's limits so the committed current values no longer match
        vm.prank(executor);
        router.updateModuleShares(moduleId, curStake + 1, curThreshold + 1);

        vm.warp(block.timestamp + easyTrack.motionDuration() + 1);
        vm.prank(makeAddr("stranger"));
        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        easyTrack.enactMotion(motionId, callData);
    }

    // --- scenario helpers ---

    function _assertShares(uint16 stake, uint16 threshold) private view {
        IStakingRouter.StakingModule memory m = router.getStakingModule(moduleId);
        assertEq(m.stakeShareLimit, stake, "stakeShareLimit");
        assertEq(m.priorityExitShareThreshold, threshold, "priorityExitShareThreshold");
    }

    /// @dev Raise the threshold (the upper bound for stake), then the stake, within the factory's max
    ///      increase deltas and keeping `newStake <= newThreshold <= 100%`.
    function _plannedIncrease() private view returns (uint16 newStake, uint16 newThreshold, bytes memory callData) {
        (uint16 curStake, uint16 curThreshold) = _currentShares();

        newThreshold = curThreshold + _min16(100, factory.maxPriorityExitShareThresholdIncrease());
        require(newThreshold <= 10000 && newThreshold > curThreshold, "no room to increase threshold");
        newStake = curStake + _min16(100, factory.maxStakeShareLimitIncrease());
        require(newStake <= newThreshold && newStake > curStake, "no room to increase stake");

        callData = abi.encode(curStake, newStake, curThreshold, newThreshold);
    }

    /// @dev Lower the stake, then the threshold, within the factory's max decrease deltas and keeping
    ///      `newStake <= newThreshold`.
    function _plannedDecrease() private view returns (uint16 newStake, uint16 newThreshold, bytes memory callData) {
        (uint16 curStake, uint16 curThreshold) = _currentShares();

        newStake = curStake - _min16(_min16(100, factory.maxStakeShareLimitDecrease()), curStake);
        newThreshold =
            curThreshold - _min16(_min16(100, factory.maxPriorityExitShareThresholdDecrease()), curThreshold - newStake);
        require(newStake < curStake && newThreshold < curThreshold, "no room to decrease");

        callData = abi.encode(curStake, newStake, curThreshold, newThreshold);
    }

    function _currentShares() private view returns (uint16 curStake, uint16 curThreshold) {
        IStakingRouter.StakingModule memory m = router.getStakingModule(moduleId);
        return (m.stakeShareLimit, m.priorityExitShareThreshold);
    }

    function _min16(uint16 a, uint16 b) private pure returns (uint16) {
        return a < b ? a : b;
    }
}
