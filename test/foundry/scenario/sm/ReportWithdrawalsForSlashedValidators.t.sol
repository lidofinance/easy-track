// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { Vm } from "forge-std/Vm.sol";
import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import { IBaseModule, WithdrawnValidatorInfo } from "../../interfaces/External.sol";
import { IReportWithdrawalsForSlashedValidators } from "../../interfaces/Factories.sol";

/// @notice Deployed `ReportWithdrawalsForSlashedValidators` (deployed-sm-<chain>.json): a motion
///         reports a slashed validator as withdrawn.
abstract contract ReportWithdrawalsForSlashedValidatorsScenario is EasyTrackScenarioBase {
    IReportWithdrawalsForSlashedValidators internal factory;
    IBaseModule internal module;

    function _factoryKey() internal pure virtual returns (string memory);

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        factory = IReportWithdrawalsForSlashedValidators(_factoryAddress(cfg.smArtifact, _factoryKey()));
        module = IBaseModule(factory.module());
        subject = address(factory);
        creator = factory.trustedCaller();
    }

    function test_reportsSlashedValidatorAsWithdrawn() external onlyForked {
        (uint256 nodeOperatorId, uint256 keyIndex) = _givenSlashedValidator();

        // preconditions: the key is deposited, slashed, and not yet withdrawn.
        (,,,,,, uint256 depositedBefore,) = module.getNodeOperatorSummary(nodeOperatorId);
        assertGe(depositedBefore, 1, "setup: key not deposited");
        assertTrue(module.isValidatorSlashed(nodeOperatorId, keyIndex), "setup: validator not slashed");
        assertFalse(module.isValidatorWithdrawn(nodeOperatorId, keyIndex), "setup: already withdrawn");

        vm.recordLogs();
        enact(_encodeWithdrawn(nodeOperatorId, keyIndex));

        // state: marked withdrawn, still flagged slashed.
        assertTrue(module.isValidatorWithdrawn(nodeOperatorId, keyIndex), "validator not marked withdrawn");
        assertTrue(module.isValidatorSlashed(nodeOperatorId, keyIndex), "slashed flag lost");

        // event: the module reported the withdrawal carrying our exit balance & slashing penalty.
        _assertValidatorWithdrawn(vm.getRecordedLogs(), nodeOperatorId, keyIndex, 32 ether, 1 ether);

        // re-reporting the same (already-withdrawn) validator is a no-op.
        enact(_encodeWithdrawn(nodeOperatorId, keyIndex));
        assertTrue(module.isValidatorWithdrawn(nodeOperatorId, keyIndex), "idempotent re-report changed state");
    }

    function test_revertsOnZeroSlashingPenalty() external onlyForked {
        // A slashed validator must be reported with a positive penalty; a zero penalty is rejected.
        (uint256 nodeOperatorId, uint256 keyIndex) = _givenSlashedValidator();

        bytes memory callData = _encodeWithdrawn(nodeOperatorId, keyIndex, 32 ether, 0);
        vm.prank(creator);
        vm.expectRevert("INVALID_SLASHING_PENALTY");
        easyTrack.createMotion(subject, callData);
    }

    function test_revertsOnZeroExitBalance() external onlyForked {
        // A withdrawn validator must be reported with a positive exit balance; zero is rejected.
        (uint256 nodeOperatorId, uint256 keyIndex) = _givenSlashedValidator();

        bytes memory callData = _encodeWithdrawn(nodeOperatorId, keyIndex, 0, 1 ether);
        vm.prank(creator);
        vm.expectRevert("ZERO_EXIT_BALANCE");
        easyTrack.createMotion(subject, callData);
    }

    /// @dev Assert the module emitted `ValidatorWithdrawn` for the operator with the expected exit
    ///      balance and slashing penalty (the charge).
    function _assertValidatorWithdrawn(
        Vm.Log[] memory logs,
        uint256 nodeOperatorId,
        uint256 keyIndex,
        uint256 exitBalance,
        uint256 slashingPenalty
    ) private {
        bytes32 topic0 = keccak256("ValidatorWithdrawn(uint256,uint256,uint256,uint256,bytes)");
        for (uint256 i; i < logs.length; ++i) {
            if (logs[i].emitter != address(module) || logs[i].topics[0] != topic0) continue;
            assertEq(uint256(logs[i].topics[1]), nodeOperatorId, "ValidatorWithdrawn: nodeOperatorId");
            (uint256 loggedKeyIndex, uint256 loggedExitBalance, uint256 loggedSlashingPenalty,) =
                abi.decode(logs[i].data, (uint256, uint256, uint256, bytes));
            assertEq(loggedKeyIndex, keyIndex, "ValidatorWithdrawn: keyIndex");
            assertEq(loggedExitBalance, exitBalance, "ValidatorWithdrawn: exitBalance");
            assertEq(loggedSlashingPenalty, slashingPenalty, "ValidatorWithdrawn: slashingPenalty (charge)");
            return;
        }
        revert("ValidatorWithdrawn not emitted by module");
    }

    // --- scenario helpers ---

    function _givenSlashedValidator() private returns (uint256 nodeOperatorId, uint256 keyIndex) {
        nodeOperatorId = _createDepositedOperator(module);
        keyIndex = 0;
        _grantRole(address(module), "VERIFIER_ROLE", address(this));
        module.reportValidatorSlashing(nodeOperatorId, keyIndex);
    }

    function _encodeWithdrawn(uint256 nodeOperatorId, uint256 keyIndex) private pure returns (bytes memory) {
        return _encodeWithdrawn(nodeOperatorId, keyIndex, 32 ether, 1 ether);
    }

    function _encodeWithdrawn(uint256 nodeOperatorId, uint256 keyIndex, uint256 exitBalance, uint256 slashingPenalty)
        private
        pure
        returns (bytes memory)
    {
        WithdrawnValidatorInfo[] memory infos = new WithdrawnValidatorInfo[](1);
        infos[0] = WithdrawnValidatorInfo({
            nodeOperatorId: nodeOperatorId,
            keyIndex: keyIndex,
            exitBalance: exitBalance,
            slashingPenalty: slashingPenalty,
            isSlashed: true
        });
        return abi.encode(infos);
    }
}

contract ReportWithdrawalsForSlashedValidatorsCSMScenario is ReportWithdrawalsForSlashedValidatorsScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "ReportWithdrawalsForSlashedValidators:CSM";
    }
}

contract ReportWithdrawalsForSlashedValidatorsCMScenario is ReportWithdrawalsForSlashedValidatorsScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "ReportWithdrawalsForSlashedValidators:CM";
    }

    function _prepareCuratedOperator(IBaseModule module_, uint256 nodeOperatorId) internal override {
        _setupCuratedGroupAndCurve(module_, nodeOperatorId);
    }
}
