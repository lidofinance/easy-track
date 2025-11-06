// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../interfaces/IStakingRouter.sol";

/// @author swissarmytowel
/// @notice Helper contract with stub implementation of StakingRouter
contract StakingRouterStub is IStakingRouter {
    mapping(uint256 => StakingModule) internal _stakingModules;

    function getStakingModule(
        uint256 _stakingModuleId
    ) external view override returns (StakingModule memory) {
        return _stakingModules[_stakingModuleId];
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
}
