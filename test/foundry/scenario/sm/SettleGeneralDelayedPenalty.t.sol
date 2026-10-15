// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IAccounting, IBaseModule} from "test/foundry/interfaces/External.sol";
import {ISettleGeneralDelayedPenalty} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `SettleGeneralDelayedPenalty` factories of `deployed-sm-<chain>.json`: a
///         motion settles a general delayed penalty locked on an operator's bond
abstract contract SettleGeneralDelayedPenaltyTest is EasyTrackScenarioBase {
    /// @dev `SettleGeneralDelayedPenalty.LockInfo`
    struct LockInfo {
        uint256 nodeOperatorId;
        uint256 nonce;
    }

    bytes32 internal constant REPORT_GENERAL_DELAYED_PENALTY_ROLE =
        keccak256("REPORT_GENERAL_DELAYED_PENALTY_ROLE");

    bytes32 internal constant PENALTY_ID = keccak256("SCENARIO_PENALTY");
    bytes32 internal constant SECOND_PENALTY_ID = keccak256("SECOND_SCENARIO_PENALTY");
    uint256 internal constant PENALTY_AMOUNT = 0.01 ether;

    IBaseModule internal module;
    IAccounting internal accounting;

    function _factoryKey() internal pure virtual returns (string memory);

    function setUp() public {
        _forkAndInitialize();

        ISettleGeneralDelayedPenalty factory =
            ISettleGeneralDelayedPenalty(_factoryAddress(config.smArtifact, _factoryKey()));
        module = IBaseModule(factory.module());
        accounting = IAccounting(factory.accounting());

        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
    }

    // python: test_settle_general_delayed_penalty_scenario
    function testFork_SettlesLockedPenalty() external {
        (uint256 nodeOperatorId, uint256 nonce) = _createOperatorWithLockedPenalty();
        // the reported penalty + the module's fixed additional fine
        uint256 lockedBond = accounting.getLockedBond(nodeOperatorId);
        bytes memory callData = _encodeLocks(nodeOperatorId, nonce);
        uint256 motionId = _createMotion(callData);

        vm.expectEmit(address(module));
        emit IBaseModule.GeneralDelayedPenaltySettled(nodeOperatorId, lockedBond);

        _enactMotion(motionId, callData);

        assertEq(accounting.getLockedBond(nodeOperatorId), 0, "getLockedBond");
    }

    function testFork_SettlesMultipleLockedPenalties() external {
        (uint256 firstOperatorId, uint256 firstNonce) = _createOperatorWithLockedPenalty();
        (uint256 secondOperatorId, uint256 secondNonce) = _createOperatorWithLockedPenalty();
        uint256 firstLockedBond = accounting.getLockedBond(firstOperatorId);
        uint256 secondLockedBond = accounting.getLockedBond(secondOperatorId);

        // the factory requires ascending operator ids
        assertLt(firstOperatorId, secondOperatorId, "setup: ascending operator ids");

        LockInfo[] memory locks = new LockInfo[](2);
        locks[0] = LockInfo({nodeOperatorId: firstOperatorId, nonce: firstNonce});
        locks[1] = LockInfo({nodeOperatorId: secondOperatorId, nonce: secondNonce});
        bytes memory callData = abi.encode(locks);
        uint256 motionId = _createMotion(callData);

        vm.expectEmit(address(module));
        emit IBaseModule.GeneralDelayedPenaltySettled(firstOperatorId, firstLockedBond);

        vm.expectEmit(address(module));
        emit IBaseModule.GeneralDelayedPenaltySettled(secondOperatorId, secondLockedBond);

        _enactMotion(motionId, callData);

        assertEq(accounting.getLockedBond(firstOperatorId), 0, "first getLockedBond");
        assertEq(accounting.getLockedBond(secondOperatorId), 0, "second getLockedBond");
    }

    function testFork_RevertWhen_NothingToSettle() external {
        uint256 nodeOperatorId = _createDepositedOperator(module);
        bytes memory callData =
            _encodeLocks(nodeOperatorId, accounting.getBondLockNonce(nodeOperatorId));

        vm.prank(creator);
        vm.expectRevert("NO_LOCK_TO_SETTLE");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    function testFork_RevertWhen_LockNonceChangesBeforeEnact() external {
        (uint256 nodeOperatorId, uint256 nonce) = _createOperatorWithLockedPenalty();
        bytes memory callData = _encodeLocks(nodeOperatorId, nonce);
        uint256 motionId = _createMotion(callData);

        // Locking another penalty bumps the operator's bond-lock nonce
        module.reportGeneralDelayedPenalty(
            nodeOperatorId, SECOND_PENALTY_ID, PENALTY_AMOUNT, "second scenario penalty"
        );

        assertNotEq(accounting.getBondLockNonce(nodeOperatorId), nonce, "setup: getBondLockNonce");

        _passMotionDuration();

        vm.prank(stranger);
        vm.expectRevert("INVALID_LOCK_NONCE");
        easyTrack.enactMotion(motionId, callData);
    }

    function testFork_RevertWhen_AlreadySettledBeforeEnact() external {
        (uint256 nodeOperatorId, uint256 nonce) = _createOperatorWithLockedPenalty();
        bytes memory callData = _encodeLocks(nodeOperatorId, nonce);
        uint256 motionId = _createMotion(callData);

        // Settle the penalty directly before the motion is enacted
        uint256[] memory nodeOperatorIds = new uint256[](1);
        nodeOperatorIds[0] = nodeOperatorId;
        uint256[] memory nonces = new uint256[](1);
        nonces[0] = nonce;

        vm.prank(evmScriptExecutor);
        module.settleGeneralDelayedPenalty(nodeOperatorIds, nonces);

        assertEq(accounting.getLockedBond(nodeOperatorId), 0, "setup: getLockedBond");

        _passMotionDuration();

        vm.prank(stranger);
        vm.expectRevert("NO_LOCK_TO_SETTLE");
        easyTrack.enactMotion(motionId, callData);
    }

    function _createOperatorWithLockedPenalty()
        private
        returns (uint256 nodeOperatorId, uint256 nonce)
    {
        nodeOperatorId = _createDepositedOperator(module);
        _grantRole(address(module), REPORT_GENERAL_DELAYED_PENALTY_ROLE, address(this));
        module.reportGeneralDelayedPenalty(
            nodeOperatorId, PENALTY_ID, PENALTY_AMOUNT, "scenario penalty"
        );

        assertGt(accounting.getLockedBond(nodeOperatorId), 0, "setup: getLockedBond");

        nonce = accounting.getBondLockNonce(nodeOperatorId);
    }

    function _encodeLocks(uint256 nodeOperatorId, uint256 nonce)
        private
        pure
        returns (bytes memory)
    {
        LockInfo[] memory locks = new LockInfo[](1);
        locks[0] = LockInfo({nodeOperatorId: nodeOperatorId, nonce: nonce});

        return abi.encode(locks);
    }
}

contract SettleGeneralDelayedPenaltyCSMTest is SettleGeneralDelayedPenaltyTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "SettleGeneralDelayedPenalty:CSM";
    }
}

contract SettleGeneralDelayedPenaltyCMTest is SettleGeneralDelayedPenaltyTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "SettleGeneralDelayedPenalty:CM";
    }

    function _prepareCuratedOperator(IBaseModule module_, uint256 nodeOperatorId)
        internal
        override
    {
        _makeCuratedOperatorDepositable(module_, nodeOperatorId);
    }
}
