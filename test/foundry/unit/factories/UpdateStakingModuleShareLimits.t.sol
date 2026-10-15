// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    UpdateStakingModuleShareLimits,
    IUpdateStakingModuleShareLimits
} from "contracts/EVMScriptFactories/UpdateStakingModuleShareLimits.sol";
import {IStakingRouter} from "contracts/interfaces/IStakingRouter.sol";
import {StakingRouterStub} from "contracts/test/StakingRouterStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract UpdateStakingModuleShareLimitsTest is Test {
    string internal constant FACTORY_NAME = "CSM v3";
    uint256 internal constant MODULE_ID = 3;
    uint16 internal constant CURRENT_STAKE_SHARE_LIMIT = 500;
    uint16 internal constant CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD = 9_000;
    uint16 internal constant MAX_STAKE_SHARE_LIMIT_INCREASE = 500;
    uint16 internal constant MAX_STAKE_SHARE_LIMIT_DECREASE = 400;
    uint16 internal constant MAX_PRIORITY_EXIT_SHARE_THRESHOLD_INCREASE = 300;
    uint16 internal constant MAX_PRIORITY_EXIT_SHARE_THRESHOLD_DECREASE = 200;
    uint16 internal constant MAX_BP = 10_000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    StakingRouterStub internal stakingRouterStub;
    UpdateStakingModuleShareLimits internal updateStakingModuleShareLimits;

    /// @dev python: _deploy_router and _deploy_factory, rebuilt before every test
    function setUp() public {
        stakingRouterStub = new StakingRouterStub();
        stakingRouterStub.setStakingModule(MODULE_ID, owner);
        stakingRouterStub.setModuleShares(
            MODULE_ID, CURRENT_STAKE_SHARE_LIMIT, CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD
        );

        updateStakingModuleShareLimits = _deployFactory(address(stakingRouterStub), MODULE_ID);

        vm.label(address(stakingRouterStub), "stakingRouterStub");
        vm.label(address(updateStakingModuleShareLimits), "updateStakingModuleShareLimits");
    }

    // python: test_deploy_reverts_on_zero_staking_router
    function test_RevertWhen_StakingRouterIsZero() external {
        vm.expectRevert("ZERO_STAKING_ROUTER");
        _deployFactory(address(0), MODULE_ID);
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        uint16 newStakeShareLimit = CURRENT_STAKE_SHARE_LIMIT + 200;
        uint16 newPriorityExitShareThreshold = CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD - 150;
        bytes memory callData = _callData(
            CURRENT_STAKE_SHARE_LIMIT,
            newStakeShareLimit,
            CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
            newPriorityExitShareThreshold
        );

        assertEq(updateStakingModuleShareLimits.trustedCaller(), owner, "trustedCaller");
        assertEq(updateStakingModuleShareLimits.name(), FACTORY_NAME, "name");

        bytes memory evmScript = updateStakingModuleShareLimits.createEVMScript(owner, callData);

        assertEq(
            evmScript,
            _updateModuleSharesScript(callData, newStakeShareLimit, newPriorityExitShareThreshold),
            "evmScript"
        );
    }

    // python: test_reverts_if_stake_share_limit_changed
    function test_RevertWhen_StakeShareLimitChanged() external {
        bytes memory callData = _callData(
            CURRENT_STAKE_SHARE_LIMIT,
            CURRENT_STAKE_SHARE_LIMIT + 100,
            CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
            CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD
        );

        updateStakingModuleShareLimits.createEVMScript(owner, callData);

        stakingRouterStub.setModuleShares(
            MODULE_ID, CURRENT_STAKE_SHARE_LIMIT + 1, CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD
        );

        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        updateStakingModuleShareLimits.createEVMScript(owner, callData);
    }

    // python: test_reverts_if_priority_exit_threshold_changed
    function test_RevertWhen_PriorityExitShareThresholdChanged() external {
        bytes memory callData = _callData(
            CURRENT_STAKE_SHARE_LIMIT,
            CURRENT_STAKE_SHARE_LIMIT,
            CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
            CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD + 100
        );

        updateStakingModuleShareLimits.createEVMScript(owner, callData);

        stakingRouterStub.setModuleShares(
            MODULE_ID, CURRENT_STAKE_SHARE_LIMIT, CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD + 1
        );

        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        updateStakingModuleShareLimits.createEVMScript(owner, callData);
    }

    // python: test_reverts_when_stake_share_limit_delta_exceeds_cap
    function test_RevertWhen_StakeShareLimitDeltaExceedsCap() external {
        vm.expectRevert("STAKE_SHARE_LIMIT_DELTA_EXCEEDED");
        updateStakingModuleShareLimits.createEVMScript(
            owner,
            _callData(
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_STAKE_SHARE_LIMIT + MAX_STAKE_SHARE_LIMIT_INCREASE + 1,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD
            )
        );
    }

    // python: test_reverts_when_priority_exit_threshold_delta_exceeds_cap
    function test_RevertWhen_PriorityExitShareThresholdDeltaExceedsCap() external {
        vm.expectRevert("PRIORITY_EXIT_SHARE_THRESHOLD_DELTA_EXCEEDED");
        updateStakingModuleShareLimits.createEVMScript(
            owner,
            _callData(
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD - MAX_PRIORITY_EXIT_SHARE_THRESHOLD_DECREASE
                    - 1
            )
        );
    }

    // python: test_reverts_when_new_stake_share_exceeds_new_priority_exit_threshold
    function test_RevertWhen_NewStakeShareLimitExceedsNewPriorityExitShareThreshold() external {
        vm.expectRevert("INVALID_SHARE_PARAMS");
        updateStakingModuleShareLimits.createEVMScript(
            owner,
            _callData(
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD + 1,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD
            )
        );
    }

    // python: test_reverts_when_new_priority_exit_threshold_exceeds_max_bp
    function test_RevertWhen_NewPriorityExitShareThresholdExceedsMaxBP() external {
        vm.expectRevert("INVALID_SHARE_PARAMS");
        updateStakingModuleShareLimits.createEVMScript(
            owner,
            _callData(
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
                MAX_BP + 1
            )
        );
    }

    // python: test_reverts_when_no_changes
    function test_RevertWhen_NoChanges() external {
        vm.expectRevert("NO_CHANGES");
        updateStakingModuleShareLimits.createEVMScript(
            owner,
            _callData(
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD
            )
        );
    }

    // python: test_reverts_if_staking_module_does_not_exist
    function test_RevertWhen_StakingModuleDoesNotExist() external {
        StakingRouterStub emptyStakingRouterStub = new StakingRouterStub();
        UpdateStakingModuleShareLimits factory =
            _deployFactory(address(emptyStakingRouterStub), MODULE_ID + 1);

        vm.expectRevert(StakingRouterStub.StakingModuleUnregistered.selector);
        factory.createEVMScript(owner, _callData(0, 100, 0, 100));
    }

    // python: test_decode_call_data
    function test_DecodesEVMScriptCallData() external view {
        IUpdateStakingModuleShareLimits.ModuleShareParams memory params =
            updateStakingModuleShareLimits.decodeEVMScriptCallData(_callData(1, 2, 3, 4));

        assertEq(params.currentStakeShareLimit, 1, "currentStakeShareLimit");
        assertEq(params.newStakeShareLimit, 2, "newStakeShareLimit");
        assertEq(params.currentPriorityExitShareThreshold, 3, "currentPriorityExitShareThreshold");
        assertEq(params.newPriorityExitShareThreshold, 4, "newPriorityExitShareThreshold");
    }

    // python: test_only_trusted_caller
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        updateStakingModuleShareLimits.createEVMScript(
            stranger,
            _callData(
                CURRENT_STAKE_SHARE_LIMIT,
                CURRENT_STAKE_SHARE_LIMIT + 100,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
                CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD + 100
            )
        );
    }

    /// @dev python: _deploy_factory_for_module_id, deployed by the owner
    function _deployFactory(address stakingRouter, uint256 moduleId)
        private
        returns (UpdateStakingModuleShareLimits)
    {
        vm.prank(owner);
        return new UpdateStakingModuleShareLimits(
            owner,
            FACTORY_NAME,
            stakingRouter,
            moduleId,
            MAX_STAKE_SHARE_LIMIT_INCREASE,
            MAX_STAKE_SHARE_LIMIT_DECREASE,
            MAX_PRIORITY_EXIT_SHARE_THRESHOLD_INCREASE,
            MAX_PRIORITY_EXIT_SHARE_THRESHOLD_DECREASE
        );
    }

    /// @dev python: C, eth_abi.encode of the four uint16 values
    function _callData(
        uint16 currentStakeShareLimit,
        uint16 newStakeShareLimit,
        uint16 currentPriorityExitShareThreshold,
        uint16 newPriorityExitShareThreshold
    ) private pure returns (bytes memory) {
        return abi.encode(
            currentStakeShareLimit,
            newStakeShareLimit,
            currentPriorityExitShareThreshold,
            newPriorityExitShareThreshold
        );
    }

    /// @dev python: encode_call_script of validateParams over the raw calldata, then
    /// router.updateModuleShares. The struct encodes to the same four words as the calldata
    function _updateModuleSharesScript(
        bytes memory callData,
        uint16 newStakeShareLimit,
        uint16 newPriorityExitShareThreshold
    ) private view returns (bytes memory) {
        address[] memory targets = new address[](2);
        targets[0] = address(updateStakingModuleShareLimits);
        targets[1] = address(stakingRouterStub);

        bytes[] memory datas = new bytes[](2);
        datas[0] =
            abi.encodePacked(IUpdateStakingModuleShareLimits.validateParams.selector, callData);
        datas[1] = abi.encodeWithSelector(
            IStakingRouter.updateModuleShares.selector,
            MODULE_ID,
            newStakeShareLimit,
            newPriorityExitShareThreshold
        );

        return EVMScripts.encodeCallScript(targets, datas);
    }
}
