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
            if (logs[i].emitter != address(module) || logs[i].topics.length == 0 || logs[i].topics[0] != topic0) {
                continue;
            }
            assertEq(uint256(logs[i].topics[1]), nodeOperatorId, "GeneralDelayedPenaltySettled: nodeOperatorId");
            assertEq(abi.decode(logs[i].data, (uint256)), amount, "GeneralDelayedPenaltySettled: amount (charge)");
            return;
        }
        revert("GeneralDelayedPenaltySettled not emitted by module");
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
