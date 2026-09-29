// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Vm} from "forge-std/Vm.sol";
import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IBaseModule, WithdrawnValidatorInfo} from "test/foundry/interfaces/External.sol";
import {IReportWithdrawalsForSlashedValidators} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `ReportWithdrawalsForSlashedValidators` factories of
///         `deployed-sm-<chain>.json`: a motion reports a slashed validator as withdrawn
abstract contract ReportWithdrawalsForSlashedValidatorsTest is EasyTrackScenarioBase {
    bytes32 internal constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");

    /// @dev The single key of an operator built by `_givenDepositedOperator`
    uint256 internal constant KEY_INDEX = 0;
    uint256 internal constant EXIT_BALANCE = 32 ether;
    uint256 internal constant SLASHING_PENALTY = 1 ether;

    IBaseModule internal module;

    function _factoryKey() internal pure virtual returns (string memory);

    function setUp() public {
        _forkAndInitialize();

        IReportWithdrawalsForSlashedValidators factory = IReportWithdrawalsForSlashedValidators(
            _factoryAddress(config.smArtifact, _factoryKey())
        );
        module = IBaseModule(factory.module());

        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
    }

    function testFork_ReportsSlashedValidatorAsWithdrawn() external {
        uint256 nodeOperatorId = _givenSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, EXIT_BALANCE, SLASHING_PENALTY);

        vm.recordLogs();

        _enact(callData);

        assertTrue(module.isValidatorWithdrawn(nodeOperatorId, KEY_INDEX), "isValidatorWithdrawn");
        assertTrue(module.isValidatorSlashed(nodeOperatorId, KEY_INDEX), "isValidatorSlashed");
        _assertValidatorWithdrawnEmitted(vm.getRecordedLogs(), nodeOperatorId);
    }

    function testFork_ReReportingWithdrawnValidatorIsNoOp() external {
        uint256 nodeOperatorId = _givenSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, EXIT_BALANCE, SLASHING_PENALTY);
        _enact(callData);

        _enact(callData);

        assertTrue(module.isValidatorWithdrawn(nodeOperatorId, KEY_INDEX), "isValidatorWithdrawn");
    }

    function testFork_RevertWhen_SlashingPenaltyIsZero() external {
        uint256 nodeOperatorId = _givenSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, EXIT_BALANCE, 0);

        vm.prank(creator);
        vm.expectRevert("INVALID_SLASHING_PENALTY");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    function testFork_RevertWhen_ExitBalanceIsZero() external {
        uint256 nodeOperatorId = _givenSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, 0, SLASHING_PENALTY);

        vm.prank(creator);
        vm.expectRevert("ZERO_EXIT_BALANCE");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    /// @dev A deposited operator whose only key is reported slashed and not yet withdrawn
    function _givenSlashedValidator() private returns (uint256 nodeOperatorId) {
        nodeOperatorId = _givenDepositedOperator(module);
        _givenRole(address(module), VERIFIER_ROLE, address(this));
        module.reportValidatorSlashing(nodeOperatorId, KEY_INDEX);

        (, , , , , , uint256 deposited, ) = module.getNodeOperatorSummary(nodeOperatorId);
        assertGe(deposited, KEYS_PER_OPERATOR, "setup: totalDepositedValidators");
        assertTrue(
            module.isValidatorSlashed(nodeOperatorId, KEY_INDEX),
            "setup: isValidatorSlashed"
        );
        assertFalse(
            module.isValidatorWithdrawn(nodeOperatorId, KEY_INDEX),
            "setup: isValidatorWithdrawn"
        );
    }

    /// @dev The module reported the withdrawal with the exit balance & slashing penalty of the
    ///      motion. The pubkey the event carries is not checked.
    function _assertValidatorWithdrawnEmitted(Vm.Log[] memory logs, uint256 nodeOperatorId)
        private
        view
    {
        bool emitted;
        for (uint256 i; i < logs.length; ++i) {
            if (
                logs[i].emitter != address(module) ||
                logs[i].topics[0] != IBaseModule.ValidatorWithdrawn.selector
            ) {
                continue;
            }

            emitted = true;
            assertEq(
                uint256(logs[i].topics[1]),
                nodeOperatorId,
                "ValidatorWithdrawn nodeOperatorId"
            );

            (uint256 keyIndex, uint256 exitBalance, uint256 slashingPenalty, ) = abi.decode(
                logs[i].data,
                (uint256, uint256, uint256, bytes)
            );
            assertEq(keyIndex, KEY_INDEX, "ValidatorWithdrawn keyIndex");
            assertEq(exitBalance, EXIT_BALANCE, "ValidatorWithdrawn exitBalance");
            assertEq(slashingPenalty, SLASHING_PENALTY, "ValidatorWithdrawn slashingPenalty");
        }

        assertTrue(emitted, "ValidatorWithdrawn emitted");
    }

    function _encodeWithdrawn(
        uint256 nodeOperatorId,
        uint256 exitBalance,
        uint256 slashingPenalty
    ) private pure returns (bytes memory) {
        WithdrawnValidatorInfo[] memory infos = new WithdrawnValidatorInfo[](1);
        infos[0] = WithdrawnValidatorInfo({
            nodeOperatorId: nodeOperatorId,
            keyIndex: KEY_INDEX,
            exitBalance: exitBalance,
            slashingPenalty: slashingPenalty,
            isSlashed: true
        });

        return abi.encode(infos);
    }
}

contract ReportWithdrawalsForSlashedValidatorsCSMTest is ReportWithdrawalsForSlashedValidatorsTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "ReportWithdrawalsForSlashedValidators:CSM";
    }
}

contract ReportWithdrawalsForSlashedValidatorsCMTest is ReportWithdrawalsForSlashedValidatorsTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "ReportWithdrawalsForSlashedValidators:CM";
    }

    function _prepareCuratedOperator(IBaseModule module_, uint256 nodeOperatorId)
        internal
        override
    {
        _givenCuratedOperatorDepositable(module_, nodeOperatorId);
    }
}
