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

    function test_updatesModuleShareLimits() external onlyForked {
        (uint16 newStake, uint16 newThreshold, bytes memory callData) = _plannedShareUpdate();

        enact(callData);

        _assertShares(newStake, newThreshold);
    }

    // --- scenario helpers ---

    function _assertShares(uint16 stake, uint16 threshold) private view {
        IStakingRouter.StakingModule memory m = router.getStakingModule(moduleId);
        assertEq(m.stakeShareLimit, stake, "stakeShareLimit");
        assertEq(m.priorityExitShareThreshold, threshold, "priorityExitShareThreshold");
    }

    /// @dev Pick a small, valid change to the current limits and encode the motion calldata.
    function _plannedShareUpdate() private view returns (uint16 newStake, uint16 newThreshold, bytes memory callData) {
        IStakingRouter.StakingModule memory m = router.getStakingModule(moduleId);
        uint16 curStake = m.stakeShareLimit;
        uint16 curThreshold = m.priorityExitShareThreshold;

        // Move the threshold (the upper bound for stake) within the configured max delta, then the
        // stake, keeping newStake <= newThreshold <= 100% and at least one value changed.
        uint16 thrStep = _min16(100, factory.maxPriorityExitShareThresholdIncrease());
        newThreshold = curThreshold + thrStep <= 10000
            ? curThreshold + thrStep
            : curThreshold - _min16(100, factory.maxPriorityExitShareThresholdDecrease());

        uint16 stakeStep = _min16(100, factory.maxStakeShareLimitIncrease());
        newStake = curStake + stakeStep <= newThreshold ? curStake + stakeStep : curStake;

        require(newStake != curStake || newThreshold != curThreshold, "no representable change");
        callData = abi.encode(curStake, newStake, curThreshold, newThreshold);
    }

    function _min16(uint16 a, uint16 b) private pure returns (uint16) {
        return a < b ? a : b;
    }
}
