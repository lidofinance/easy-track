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

    /// @dev The single key of an operator built by `_createDepositedOperator`
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

    // python: test_submit_withdrawals_scenario, the single validator case
    function testFork_ReportsSlashedValidatorAsWithdrawn() external {
        uint256 nodeOperatorId = _createSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, EXIT_BALANCE, SLASHING_PENALTY);

        vm.recordLogs();

        _enact(callData);

        assertTrue(module.isValidatorWithdrawn(nodeOperatorId, KEY_INDEX), "isValidatorWithdrawn");
        assertTrue(module.isValidatorSlashed(nodeOperatorId, KEY_INDEX), "isValidatorSlashed");
        _assertValidatorWithdrawnEmitted(vm.getRecordedLogs(), nodeOperatorId);
    }

    // python: test_submit_withdrawals_scenario, the two validators case
    function testFork_ReportsTwoSlashedValidatorsAsWithdrawn() external {
        uint256 firstOperatorId = _createSlashedValidator();
        uint256 secondOperatorId = _createSlashedValidator();

        // the factory requires ascending operator ids
        assertLt(firstOperatorId, secondOperatorId, "setup: ascending operator ids");

        WithdrawnValidatorInfo[] memory infos = new WithdrawnValidatorInfo[](2);
        infos[0] = _withdrawn(firstOperatorId, EXIT_BALANCE, SLASHING_PENALTY);
        infos[1] = _withdrawn(secondOperatorId, EXIT_BALANCE, SLASHING_PENALTY);
        bytes memory callData = abi.encode(infos);

        vm.recordLogs();

        _enact(callData);

        Vm.Log[] memory logs = vm.getRecordedLogs();
        assertTrue(
            module.isValidatorWithdrawn(firstOperatorId, KEY_INDEX), "first isValidatorWithdrawn"
        );
        assertTrue(
            module.isValidatorWithdrawn(secondOperatorId, KEY_INDEX), "second isValidatorWithdrawn"
        );
        _assertValidatorWithdrawnEmitted(logs, firstOperatorId);
        _assertValidatorWithdrawnEmitted(logs, secondOperatorId);
    }

    function testFork_ReReportingWithdrawnValidatorIsNoOp() external {
        uint256 nodeOperatorId = _createSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, EXIT_BALANCE, SLASHING_PENALTY);
        _enact(callData);

        _enact(callData);

        assertTrue(module.isValidatorWithdrawn(nodeOperatorId, KEY_INDEX), "isValidatorWithdrawn");
    }

    function testFork_RevertWhen_SlashingPenaltyIsZero() external {
        uint256 nodeOperatorId = _createSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, EXIT_BALANCE, 0);

        vm.prank(creator);
        vm.expectRevert("INVALID_SLASHING_PENALTY");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    function testFork_RevertWhen_ExitBalanceIsZero() external {
        uint256 nodeOperatorId = _createSlashedValidator();
        bytes memory callData = _encodeWithdrawn(nodeOperatorId, 0, SLASHING_PENALTY);

        vm.prank(creator);
        vm.expectRevert("ZERO_EXIT_BALANCE");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    /// @dev A deposited operator whose only key is reported slashed and not yet withdrawn
    function _createSlashedValidator() private returns (uint256 nodeOperatorId) {
        nodeOperatorId = _createDepositedOperator(module);
        _grantRole(address(module), VERIFIER_ROLE, address(this));
        module.reportValidatorSlashing(nodeOperatorId, KEY_INDEX);

        (,,,,,, uint256 deposited,) = module.getNodeOperatorSummary(nodeOperatorId);
        assertGe(deposited, KEYS_PER_OPERATOR, "setup: totalDepositedValidators");
        assertTrue(
            module.isValidatorSlashed(nodeOperatorId, KEY_INDEX), "setup: isValidatorSlashed"
        );
        assertFalse(
            module.isValidatorWithdrawn(nodeOperatorId, KEY_INDEX), "setup: isValidatorWithdrawn"
        );
    }

    /// @dev The module reported exactly one withdrawal of the operator, with the exit balance &
    ///      slashing penalty of the motion. The pubkey the event carries is not checked.
    function _assertValidatorWithdrawnEmitted(Vm.Log[] memory logs, uint256 nodeOperatorId)
        private
        view
    {
        uint256 count;
        for (uint256 i; i < logs.length; ++i) {
            if (
                logs[i].emitter != address(module)
                    || logs[i].topics[0] != IBaseModule.ValidatorWithdrawn.selector
                    || uint256(logs[i].topics[1]) != nodeOperatorId
            ) {
                continue;
            }

            ++count;

            (uint256 keyIndex, uint256 exitBalance, uint256 slashingPenalty,) =
                abi.decode(logs[i].data, (uint256, uint256, uint256, bytes));
            assertEq(keyIndex, KEY_INDEX, "ValidatorWithdrawn keyIndex");
            assertEq(exitBalance, EXIT_BALANCE, "ValidatorWithdrawn exitBalance");
            assertEq(slashingPenalty, SLASHING_PENALTY, "ValidatorWithdrawn slashingPenalty");
        }

        assertEq(count, 1, "ValidatorWithdrawn count");
    }

    function _encodeWithdrawn(uint256 nodeOperatorId, uint256 exitBalance, uint256 slashingPenalty)
        private
        pure
        returns (bytes memory)
    {
        WithdrawnValidatorInfo[] memory infos = new WithdrawnValidatorInfo[](1);
        infos[0] = _withdrawn(nodeOperatorId, exitBalance, slashingPenalty);

        return abi.encode(infos);
    }

    function _withdrawn(uint256 nodeOperatorId, uint256 exitBalance, uint256 slashingPenalty)
        private
        pure
        returns (WithdrawnValidatorInfo memory)
    {
        return WithdrawnValidatorInfo({
            nodeOperatorId: nodeOperatorId,
            keyIndex: KEY_INDEX,
            exitBalance: exitBalance,
            slashingPenalty: slashingPenalty,
            isSlashed: true
        });
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
        _makeCuratedOperatorDepositable(module_, nodeOperatorId);
    }
}
