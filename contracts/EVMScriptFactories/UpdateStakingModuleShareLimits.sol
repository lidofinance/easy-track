// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IStakingRouter.sol";

/// @author Lido
/// @notice Creates EVMScript to update staking module share limits in the Staking Router
contract UpdateStakingModuleShareLimits is TrustedCaller, IEVMScriptFactory {
    struct ModuleShareParams {
        uint16 currentStakeShareLimit;
        uint16 newStakeShareLimit;
        uint16 currentPriorityExitShareThreshold;
        uint16 newPriorityExitShareThreshold;
    }

    string private constant ERROR_MODULE_ID_MISMATCH = "MODULE_ID_MISMATCH";
    string private constant ERROR_CURRENT_VALUES_MISMATCH = "CURRENT_VALUES_MISMATCH";
    string private constant ERROR_SHARE_LIMITS = "SHARE_LIMITS";
    string private constant ERROR_EXIT_THRESHOLD_LIMITS = "EXIT_THRESHOLD_LIMITS";
    string private constant ERROR_NO_CHANGES = "NO_CHANGES";

    string public name;
    IStakingRouter public immutable stakingRouter;
    uint256 public immutable stakingModuleId;
    uint16 public immutable maxStakeShareLimitIncrease;
    uint16 public immutable maxStakeShareLimitDecrease;
    uint16 public immutable maxPriorityExitShareIncrease;
    uint16 public immutable maxPriorityExitShareDecrease;

    /// @notice Sets immutable configuration for the factory
    /// @param _trustedCaller Address allowed to create EVMScripts
    /// @param _name Human-readable alias of the factory instance
    /// @param _stakingRouter Address of the StakingRouter contract
    /// @param _stakingModuleId ID of the staking module managed by this factory
    /// @param _maxStakeShareLimitIncrease Max allowed increase per motion for stake share limit (in BP)
    /// @param _maxStakeShareLimitDecrease Max allowed decrease per motion for stake share limit (in BP)
    /// @param _maxPriorityExitShareIncrease Max allowed increase per motion for priority exit share (in BP)
    /// @param _maxPriorityExitShareDecrease Max allowed decrease per motion for priority exit share (in BP)
    constructor(
        address _trustedCaller,
        string memory _name,
        address _stakingRouter,
        uint256 _stakingModuleId,
        uint16 _maxStakeShareLimitIncrease,
        uint16 _maxStakeShareLimitDecrease,
        uint16 _maxPriorityExitShareIncrease,
        uint16 _maxPriorityExitShareDecrease
    ) TrustedCaller(_trustedCaller) {
        name = _name;
        stakingRouter = IStakingRouter(_stakingRouter);
        stakingModuleId = _stakingModuleId;
        maxStakeShareLimitIncrease = _maxStakeShareLimitIncrease;
        maxStakeShareLimitDecrease = _maxStakeShareLimitDecrease;
        maxPriorityExitShareIncrease = _maxPriorityExitShareIncrease;
        maxPriorityExitShareDecrease = _maxPriorityExitShareDecrease;
    }

    /// @notice Creates EVMScript that updates staking module share params via the router
    /// @param _evmScriptCallData ABI-encoded ModuleShareParams payload
    /// @return EVMScript bytes containing a call to `updateModuleShares`
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        ModuleShareParams memory params = _decodeCallData(_evmScriptCallData);
        IStakingRouter.StakingModule memory module =
            stakingRouter.getStakingModule(stakingModuleId);

        require(module.id == stakingModuleId, ERROR_MODULE_ID_MISMATCH);
        require(
            module.stakeShareLimit == params.currentStakeShareLimit &&
                module.priorityExitShareThreshold == params.currentPriorityExitShareThreshold,
            ERROR_CURRENT_VALUES_MISMATCH
        );

        _validateDeltas(params);

        bytes memory callData =
            abi.encode(stakingModuleId, params.newStakeShareLimit, params.newPriorityExitShareThreshold);

        return
            EVMScriptCreator.createEVMScript(
                address(stakingRouter),
                IStakingRouter.updateModuleShares.selector,
                callData
            );
    }

    /// @notice Helper to decode EVMScript payload used by Easy Track UI/backends
    /// @param _evmScriptCallData ABI-encoded ModuleShareParams payload
    /// @return ModuleShareParams struct with decoded values
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (ModuleShareParams memory)
    {
        return _decodeCallData(_evmScriptCallData);
    }

    function _decodeCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (ModuleShareParams memory params)
    {
        (
            params.currentStakeShareLimit,
            params.newStakeShareLimit,
            params.currentPriorityExitShareThreshold,
            params.newPriorityExitShareThreshold
        ) = abi.decode(_evmScriptCallData, (uint16, uint16, uint16, uint16));
    }

    function _validateDeltas(ModuleShareParams memory _params) private view {
        bool shareChanged = _params.currentStakeShareLimit != _params.newStakeShareLimit;
        bool exitThresholdChanged =
            _params.currentPriorityExitShareThreshold != _params.newPriorityExitShareThreshold;
        require(shareChanged || exitThresholdChanged, ERROR_NO_CHANGES);

        if (shareChanged) {
            int256 delta =
                int256(uint256(_params.newStakeShareLimit)) -
                int256(uint256(_params.currentStakeShareLimit));
            if (delta > 0) {
                require(uint256(delta) <= maxStakeShareLimitIncrease, ERROR_SHARE_LIMITS);
            } else {
                require(uint256(-delta) <= maxStakeShareLimitDecrease, ERROR_SHARE_LIMITS);
            }
        }

        if (exitThresholdChanged) {
            int256 deltaPriority =
                int256(uint256(_params.newPriorityExitShareThreshold)) -
                int256(uint256(_params.currentPriorityExitShareThreshold));
            if (deltaPriority > 0) {
                require(
                    uint256(deltaPriority) <= maxPriorityExitShareIncrease,
                    ERROR_EXIT_THRESHOLD_LIMITS
                );
            } else {
                require(
                    uint256(-deltaPriority) <= maxPriorityExitShareDecrease,
                    ERROR_EXIT_THRESHOLD_LIMITS
                );
            }
        }
    }
}
