// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../interfaces/IStakingRouter.sol";

/// @author swissarmytowel
/// @notice Helper contract with stub implementation of StakingRouter
contract StakingRouterStub is IStakingRouter {
    mapping(uint256 => StakingModule) internal _stakingModules;

    event ModuleSharesUpdated(
        uint256 indexed moduleId,
        uint16 previousStakeShareLimit,
        uint16 newStakeShareLimit,
        uint16 previousPriorityExitShareThreshold,
        uint16 newPriorityExitShareThreshold
    );

    function getStakingModule(
        uint256 _stakingModuleId
    ) external view override returns (StakingModule memory) {
        return _stakingModules[_stakingModuleId];
    }

    function updateModuleShares(
        uint256 _stakingModuleId,
        uint16 _newStakeShareLimit,
        uint16 _newPriorityExitShareThreshold
    ) external override {
        StakingModule storage module = _stakingModules[_stakingModuleId];
        uint16 previousStake = module.stakeShareLimit;
        uint16 previousPriority = module.priorityExitShareThreshold;
        module.stakeShareLimit = _newStakeShareLimit;
        module.priorityExitShareThreshold = _newPriorityExitShareThreshold;

        emit ModuleSharesUpdated(
            _stakingModuleId,
            previousStake,
            _newStakeShareLimit,
            previousPriority,
            _newPriorityExitShareThreshold
        );
    }

    function setStakingModule(uint256 _stakingModuleId, address _stakingModuleAddress) external {
        // This is a stub implementation, so we don't care about the additional parameters.
        // We want to ensure module id and address are set correctly for testing purposes.
        _stakingModules[_stakingModuleId] = StakingModule({
            id: uint24(_stakingModuleId),
            stakingModuleAddress: _stakingModuleAddress,
            stakingModuleFee: 0,
            treasuryFee: 0,
            stakeShareLimit: 0,
            status: 1, // Active
            name: "Stub Module",
            lastDepositAt: 0,
            lastDepositBlock: 0,
            exitedValidatorsCount: 0,
            priorityExitShareThreshold: 0,
            maxDepositsPerBlock: 0,
            minDepositBlockDistance: 0
        });
    }

    function setModuleShares(
        uint256 _stakingModuleId,
        uint16 _stakeShareLimit,
        uint16 _priorityExitShareThreshold
    ) external {
        StakingModule storage module = _stakingModules[_stakingModuleId];
        module.id = uint24(_stakingModuleId);
        module.stakeShareLimit = _stakeShareLimit;
        module.priorityExitShareThreshold = _priorityExitShareThreshold;
    }
}
