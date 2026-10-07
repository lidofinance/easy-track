// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

// -----------------------------------------------------------------------------
// Public getters of the deployed Easy Track EVM-script factories under test.
// Each interface name matches its factory contract (contracts/EVMScriptFactories/*), except
// `INodeOperatorsFactory`, the getters the nine SimpleDVT node operator factories share.
// -----------------------------------------------------------------------------

interface IUpdateStakingModuleShareLimits {
    struct ModuleShareParams {
        uint16 currentStakeShareLimit;
        uint16 newStakeShareLimit;
        uint16 currentPriorityExitShareThreshold;
        uint16 newPriorityExitShareThreshold;
    }

    /// @dev The first call of every script the factory builds, named in its permissions
    function validateParams(ModuleShareParams memory params) external view;

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
    /// @dev The first call of every script the factory builds, named in its permissions
    function validateInputData(
        address gate,
        bytes32 currentTreeRoot,
        string memory currentTreeCid,
        bytes32 newTreeRoot,
        string memory newTreeCid
    ) external view;

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

interface ISetDepositsReserveTarget {
    function trustedCaller() external view returns (address);

    function lido() external view returns (address);

    function MAX_DEPOSITS_RESERVE_TARGET() external view returns (uint256);
}

/// @notice `IncreaseVettedValidatorsLimit` has no trusted caller: its motions come from the
///         operator's manager or reward address.
interface INodeOperatorsFactory {
    function trustedCaller() external view returns (address);

    function nodeOperatorsRegistry() external view returns (address);
}

interface IAddNodeOperators is INodeOperatorsFactory {
    function acl() external view returns (address);
}
