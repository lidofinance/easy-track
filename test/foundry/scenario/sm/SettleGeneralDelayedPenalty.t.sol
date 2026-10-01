// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { Vm } from "forge-std/Vm.sol";
import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import { IBaseModule, IAccounting } from "../../interfaces/External.sol";
import { ISettleGeneralDelayedPenalty } from "../../interfaces/Factories.sol";

/// @notice Deployed `SettleGeneralDelayedPenalty` (deployed-sm-<chain>.json): a motion settles a
///         general delayed penalty locked on an operator's bond.
abstract contract SettleGeneralDelayedPenaltyScenario is EasyTrackScenarioBase {
    struct LockInfo {
        uint256 nodeOperatorId;
        uint256 nonce;
    }

    uint256 internal constant PENALTY = 1e16;

    ISettleGeneralDelayedPenalty internal factory;
    IBaseModule internal module;
    IAccounting internal accounting;

    function _factoryKey() internal pure virtual returns (string memory);

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        factory = ISettleGeneralDelayedPenalty(_factoryAddress(cfg.smArtifact, _factoryKey()));
        module = IBaseModule(factory.module());
        accounting = IAccounting(factory.accounting());
        subject = address(factory);
        creator = factory.trustedCaller();
    }

    function test_settlesLockedPenalty() external onlyForked {
        (uint256 nodeOperatorId, uint256 nonce) = _givenOperatorWithLockedPenalty();
        uint256 locked = accounting.getLockedBond(nodeOperatorId); // reported penalty + the fixed additional fine

        vm.recordLogs();
        enact(_encodeLocks(nodeOperatorId, nonce));

        // No locked bond remains, and the module reported it settled for the full locked amount (the charge).
        assertEq(accounting.getLockedBond(nodeOperatorId), 0, "locked bond not cleared");
        _assertPenaltySettled(vm.getRecordedLogs(), nodeOperatorId, locked);
    }

    function test_settlesMultipleLockedPenalties() external onlyForked {
        (uint256 op1, uint256 nonce1) = _givenOperatorWithLockedPenalty();
        (uint256 op2, uint256 nonce2) = _givenOperatorWithLockedPenalty();
        assertLt(op1, op2, "setup: operators must be ascending for the sorted list");
        uint256 locked1 = accounting.getLockedBond(op1);
        uint256 locked2 = accounting.getLockedBond(op2);

        LockInfo[] memory locks = new LockInfo[](2);
        locks[0] = LockInfo({ nodeOperatorId: op1, nonce: nonce1 });
        locks[1] = LockInfo({ nodeOperatorId: op2, nonce: nonce2 });

        vm.recordLogs();
        enact(abi.encode(locks));

        assertEq(accounting.getLockedBond(op1), 0, "op1 not settled");
        assertEq(accounting.getLockedBond(op2), 0, "op2 not settled");
        Vm.Log[] memory logs = vm.getRecordedLogs();
        _assertPenaltySettled(logs, op1, locked1);
        _assertPenaltySettled(logs, op2, locked2);
    }

    function test_revertsWhenNothingToSettle() external onlyForked {
        // An operator with no locked penalty — the factory rejects the motion at creation.
        uint256 nodeOperatorId = _createDepositedOperator(module);

        bytes memory callData = _encodeLocks(nodeOperatorId, accounting.getBondLockNonce(nodeOperatorId));
        vm.prank(creator);
        vm.expectRevert("NO_LOCK_TO_SETTLE");
        easyTrack.createMotion(subject, callData);
    }

    function test_revertsWhenLockNonceChangesBeforeEnact() external onlyForked {
        (uint256 nodeOperatorId, uint256 nonce) = _givenOperatorWithLockedPenalty();
        bytes memory callData = _encodeLocks(nodeOperatorId, nonce);

        // Create the motion while the committed nonce still matches on-chain.
        vm.prank(creator);
        uint256 motionId = easyTrack.createMotion(subject, callData);

        // Locking another penalty bumps the operator's bond-lock nonce.
        module.reportGeneralDelayedPenalty(nodeOperatorId, keccak256("SECOND_PENALTY"), PENALTY, "second");
        assertTrue(accounting.getBondLockNonce(nodeOperatorId) != nonce, "setup: lock nonce did not change");

        // Enact re-validates the (now stale) committed nonce and reverts.
        vm.warp(block.timestamp + easyTrack.motionDuration() + 1);
        vm.prank(makeAddr("stranger"));
        vm.expectRevert("INVALID_LOCK_NONCE");
        easyTrack.enactMotion(motionId, callData);
    }

    function test_revertsWhenAlreadySettledBeforeEnact() external onlyForked {
        (uint256 op, uint256 nonce) = _givenOperatorWithLockedPenalty();
        bytes memory callData = _encodeLocks(op, nonce);

        vm.prank(creator);
        uint256 motionId = easyTrack.createMotion(subject, callData);

        // settle the penalty directly, before the motion is enacted
        uint256[] memory ids = new uint256[](1);
        ids[0] = op;
        uint256[] memory nonces = new uint256[](1);
        nonces[0] = nonce;
        vm.prank(executor);
        module.settleGeneralDelayedPenalty(ids, nonces);
        assertEq(accounting.getLockedBond(op), 0, "setup: not pre-settled");

        // the motion re-validates at enactment: nothing is left to settle, so it reverts (not a no-op).
        vm.warp(block.timestamp + easyTrack.motionDuration() + 1);
        vm.prank(makeAddr("stranger"));
        vm.expectRevert("NO_LOCK_TO_SETTLE");
        easyTrack.enactMotion(motionId, callData);
    }

    // --- scenario helpers ---

    function _givenOperatorWithLockedPenalty() private returns (uint256 nodeOperatorId, uint256 nonce) {
        nodeOperatorId = _createDepositedOperator(module);
        _grantRole(address(module), "REPORT_GENERAL_DELAYED_PENALTY_ROLE", address(this));
        module.reportGeneralDelayedPenalty(nodeOperatorId, keccak256("SCENARIO_PREP"), PENALTY, "scenario prep");
        assertGt(accounting.getLockedBond(nodeOperatorId), 0, "setup: bond not locked");
        nonce = accounting.getBondLockNonce(nodeOperatorId);
    }

    /// @dev Assert the module emitted `GeneralDelayedPenaltySettled` for the operator with the amount charged.
    function _assertPenaltySettled(Vm.Log[] memory logs, uint256 nodeOperatorId, uint256 amount) private {
        bytes32 topic0 = keccak256("GeneralDelayedPenaltySettled(uint256,uint256)");
        for (uint256 i; i < logs.length; ++i) {
            if (
                logs[i].emitter != address(module) || logs[i].topics.length < 2 || logs[i].topics[0] != topic0
                    || uint256(logs[i].topics[1]) != nodeOperatorId
            ) {
                continue;
            }
            assertEq(abi.decode(logs[i].data, (uint256)), amount, "GeneralDelayedPenaltySettled: amount (charge)");
            return;
        }
        revert("GeneralDelayedPenaltySettled not emitted for operator");
    }

    function _encodeLocks(uint256 nodeOperatorId, uint256 nonce) private pure returns (bytes memory) {
        LockInfo[] memory locks = new LockInfo[](1);
        locks[0] = LockInfo({ nodeOperatorId: nodeOperatorId, nonce: nonce });
        return abi.encode(locks);
    }
}

contract SettleGeneralDelayedPenaltyCSMScenario is SettleGeneralDelayedPenaltyScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "SettleGeneralDelayedPenalty:CSM";
    }
}

contract SettleGeneralDelayedPenaltyCMScenario is SettleGeneralDelayedPenaltyScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "SettleGeneralDelayedPenalty:CM";
    }

    function _prepareCuratedOperator(IBaseModule module_, uint256 nodeOperatorId) internal override {
        _setupCuratedGroupAndCurve(module_, nodeOperatorId);
    }
}
