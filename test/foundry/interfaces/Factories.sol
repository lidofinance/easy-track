// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

// -----------------------------------------------------------------------------
// Public getters of the deployed Easy Track EVM-script factories under test.
// Each interface name matches its factory contract (contracts/EVMScriptFactories/*).
// -----------------------------------------------------------------------------

interface IUpdateStakingModuleShareLimits {
    function trustedCaller() external view returns (address);

    function stakingRouter() external view returns (address);

    function stakingModuleId() external view returns (uint256);

    function maxStakeShareLimitIncrease() external view returns (uint16);

    function maxStakeShareLimitDecrease() external view returns (uint16);

    function maxPriorityExitShareThresholdIncrease() external view returns (uint16);

    function maxPriorityExitShareThresholdDecrease() external view returns (uint16);
}

interface IAllowConsolidationPair {
    function consolidationMigrator() external view returns (address);

    function stakingRouter() external view returns (address);

    function sourceModuleId() external view returns (uint256);

    function targetModuleId() external view returns (uint256);
}

interface ISettleGeneralDelayedPenalty {
    function trustedCaller() external view returns (address);

    function module() external view returns (address);

    function accounting() external view returns (address);
}

interface ISetMerkleGateTree {
    function trustedCaller() external view returns (address);
}

interface IReportWithdrawalsForSlashedValidators {
    function trustedCaller() external view returns (address);

    function module() external view returns (address);
}

interface ICreateOrUpdateOperatorGroup {
    function trustedCaller() external view returns (address);

    function module() external view returns (address);

    function metaRegistry() external view returns (address);

    function stakingRouter() external view returns (address);

    function allowedExternalModuleId() external view returns (uint256);
}
