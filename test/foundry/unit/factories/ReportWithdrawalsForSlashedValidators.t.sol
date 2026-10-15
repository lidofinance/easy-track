// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    ReportWithdrawalsForSlashedValidators
} from "contracts/EVMScriptFactories/ReportWithdrawalsForSlashedValidators.sol";
import {IBaseModule, WithdrawnValidatorInfo} from "contracts/interfaces/IBaseModule.sol";
import {BaseModuleStub} from "contracts/test/BaseModuleStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract ReportWithdrawalsForSlashedValidatorsTest is Test {
    string internal constant FACTORY_NAME = "CSM v3";
    uint256 internal constant NODE_OPERATORS_COUNT = 1000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    BaseModuleStub internal baseModuleStub;
    ReportWithdrawalsForSlashedValidators internal reportWithdrawalsForSlashedValidators;

    function setUp() public {
        baseModuleStub = new BaseModuleStub();
        baseModuleStub.mock_setNodeOperatorsCount(NODE_OPERATORS_COUNT);

        vm.prank(owner);
        reportWithdrawalsForSlashedValidators =
            new ReportWithdrawalsForSlashedValidators(owner, FACTORY_NAME, address(baseModuleStub));

        vm.label(address(baseModuleStub), "baseModuleStub");
        vm.label(
            address(reportWithdrawalsForSlashedValidators), "reportWithdrawalsForSlashedValidators"
        );
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(reportWithdrawalsForSlashedValidators.trustedCaller(), owner, "trustedCaller");
        assertEq(reportWithdrawalsForSlashedValidators.name(), FACTORY_NAME, "name");
        assertEq(
            address(reportWithdrawalsForSlashedValidators.module()),
            address(baseModuleStub),
            "module"
        );
    }

    // python: test_deploy_reverts_on_zero_module_address
    function test_RevertWhen_ModuleIsZero() external {
        vm.expectRevert("ZERO_MODULE_ADDRESS");
        new ReportWithdrawalsForSlashedValidators(owner, FACTORY_NAME, address(0));
    }

    // python: test_create_evm_script_reverts_if_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        reportWithdrawalsForSlashedValidators.createEVMScript(stranger, "");
    }

    // python: test_create_evm_script_reverts_if_empty_withdrawal_list
    function test_RevertWhen_ValidatorInfoListIsEmpty() external {
        WithdrawnValidatorInfo[] memory infos = new WithdrawnValidatorInfo[](0);

        vm.expectRevert("EMPTY_VALIDATOR_INFO_LIST");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_zero_exit_balance, single entry
    function test_RevertWhen_ExitBalanceIsZero() external {
        WithdrawnValidatorInfo[] memory infos = _infos(_info(1, 1, 0, 1, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("ZERO_EXIT_BALANCE");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_zero_exit_balance, second entry after a valid one
    function test_RevertWhen_ExitBalanceIsZeroInSecondEntry() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 0, 100500, 16, true), _info(1, 1, 0, 1, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("ZERO_EXIT_BALANCE");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_zero_slashing_penalty, single entry
    function test_RevertWhen_SlashingPenaltyIsZero() external {
        WithdrawnValidatorInfo[] memory infos = _infos(_info(1, 1, 1, 0, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("INVALID_SLASHING_PENALTY");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_zero_slashing_penalty, second entry after a valid
    // one
    function test_RevertWhen_SlashingPenaltyIsZeroInSecondEntry() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 0, 100500, 16, true), _info(1, 1, 1, 0, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("INVALID_SLASHING_PENALTY");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_non_existing_operator, single entry
    function test_RevertWhen_OperatorDoesNotExist() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(NODE_OPERATORS_COUNT + 1, 1, 1, 1, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("OPERATOR_DOES_NOT_EXIST");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_non_existing_operator, second entry after a valid
    // one
    function test_RevertWhen_OperatorDoesNotExistInSecondEntry() external {
        WithdrawnValidatorInfo[] memory infos = _infos(
            _info(0, 0, 100500, 16, true), _info(NODE_OPERATORS_COUNT + 1, 3, 30000, 0, true)
        );

        _markValidatorsSlashed(infos);

        vm.expectRevert("OPERATOR_DOES_NOT_EXIST");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_is_slashed_is_not_set, single entry
    function test_RevertWhen_IsSlashedIsNotSet() external {
        WithdrawnValidatorInfo[] memory infos = _infos(_info(0, 1, 1, 1, false));

        vm.expectRevert("IS_SLASHED_IS_NOT_SET");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_is_slashed_is_not_set, two entries
    function test_RevertWhen_IsSlashedIsNotSetWithTwoEntries() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 0, 100500, 16, false), _info(1, 3, 30000, 0, false));

        vm.expectRevert("IS_SLASHED_IS_NOT_SET");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_validator_not_slashed
    function test_RevertWhen_ValidatorIsNotSlashed() external {
        WithdrawnValidatorInfo[] memory infos = _infos(_info(0, 0, 100500, 16, true));

        vm.expectRevert("VALIDATOR_NOT_SLASHED");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_not_sorted[descending_operator_ids]
    function test_RevertWhen_OperatorIdsAreDescending() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(1, 0, 100500, 16, true), _info(0, 1, 30000, 1, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("NOT_SORTED");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_not_sorted[same_operator_id_descending_key_indices]
    function test_RevertWhen_KeyIndicesAreDescendingForSameOperator() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 5, 100500, 16, true), _info(0, 1, 30000, 1, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("NOT_SORTED");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script_reverts_if_not_sorted[same_operator_id_duplicate_key_indices]
    function test_RevertWhen_KeyIndicesAreDuplicatedForSameOperator() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 1, 100500, 16, true), _info(0, 1, 30000, 1, true));

        _markValidatorsSlashed(infos);

        vm.expectRevert("NOT_SORTED");
        reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));
    }

    // python: test_create_evm_script, single entry
    function test_CreatesEVMScript() external {
        WithdrawnValidatorInfo[] memory infos = _infos(_info(0, 0, 100500, 16, true));

        _markValidatorsSlashed(infos);

        bytes memory evmScript =
            reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));

        assertEq(evmScript, _reportSlashedWithdrawnValidatorsScript(infos), "evmScript");
    }

    // python: test_create_evm_script, two operators
    function test_CreatesEVMScriptForTwoOperators() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 0, 100500, 16, true), _info(1, 3, 30000, 1, true));

        _markValidatorsSlashed(infos);

        bytes memory evmScript =
            reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));

        assertEq(evmScript, _reportSlashedWithdrawnValidatorsScript(infos), "evmScript");
    }

    // python: test_create_evm_script[same_operator_id_increasing_key_indices]
    function test_CreatesEVMScriptForSameOperatorWithIncreasingKeyIndices() external {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 1, 100500, 16, true), _info(0, 5, 30000, 1, true));

        _markValidatorsSlashed(infos);

        bytes memory evmScript =
            reportWithdrawalsForSlashedValidators.createEVMScript(owner, abi.encode(infos));

        assertEq(evmScript, _reportSlashedWithdrawnValidatorsScript(infos), "evmScript");
    }

    // python: test_decode_evm_script_call_data, empty list
    function test_DecodesEmptyEVMScriptCallData() external view {
        WithdrawnValidatorInfo[] memory infos = new WithdrawnValidatorInfo[](0);

        WithdrawnValidatorInfo[] memory decoded =
            reportWithdrawalsForSlashedValidators.decodeEVMScriptCallData(abi.encode(infos));

        _assertInfosEq(decoded, infos);
    }

    // python: test_decode_evm_script_call_data, single entry with zero values
    function test_DecodesEVMScriptCallDataWithZeroValues() external view {
        WithdrawnValidatorInfo[] memory infos = _infos(_info(0, 0, 0, 0, true));

        WithdrawnValidatorInfo[] memory decoded =
            reportWithdrawalsForSlashedValidators.decodeEVMScriptCallData(abi.encode(infos));

        _assertInfosEq(decoded, infos);
    }

    // python: test_decode_evm_script_call_data, single entry
    function test_DecodesEVMScriptCallData() external view {
        WithdrawnValidatorInfo[] memory infos = _infos(_info(1, 2, 100500, 16, true));

        WithdrawnValidatorInfo[] memory decoded =
            reportWithdrawalsForSlashedValidators.decodeEVMScriptCallData(abi.encode(infos));

        _assertInfosEq(decoded, infos);
    }

    // python: test_decode_evm_script_call_data, two operators
    function test_DecodesEVMScriptCallDataForTwoOperators() external view {
        WithdrawnValidatorInfo[] memory infos =
            _infos(_info(0, 0, 100500, 16, true), _info(1, 3, 30000, 0, true));

        WithdrawnValidatorInfo[] memory decoded =
            reportWithdrawalsForSlashedValidators.decodeEVMScriptCallData(abi.encode(infos));

        _assertInfosEq(decoded, infos);
    }

    // python: test_decode_evm_script_call_data_reverts_on_invalid_calldata[empty]
    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        reportWithdrawalsForSlashedValidators.decodeEVMScriptCallData("");
    }

    // python: test_decode_evm_script_call_data_reverts_on_invalid_calldata[malformed]
    function test_RevertWhen_DecodingMalformedCallData() external {
        vm.expectRevert(bytes(""));
        reportWithdrawalsForSlashedValidators.decodeEVMScriptCallData(hex"01");
    }

    /// @dev python: mark_validators_slashed. Marks every entry the factory would otherwise accept
    function _markValidatorsSlashed(WithdrawnValidatorInfo[] memory infos) private {
        uint256 nodeOperatorsCount = baseModuleStub.getNodeOperatorsCount();

        for (uint256 i; i < infos.length; ++i) {
            WithdrawnValidatorInfo memory info = infos[i];
            bool markable = info.nodeOperatorId < nodeOperatorsCount && info.exitBalance > 0
                && info.slashingPenalty > 0 && info.isSlashed;

            if (markable) {
                baseModuleStub.mock_setValidatorSlashed(info.nodeOperatorId, info.keyIndex, true);
            }
        }
    }

    function _info(
        uint256 nodeOperatorId,
        uint256 keyIndex,
        uint256 exitBalance,
        uint256 slashingPenalty,
        bool isSlashed
    ) private pure returns (WithdrawnValidatorInfo memory) {
        return WithdrawnValidatorInfo({
            nodeOperatorId: nodeOperatorId,
            keyIndex: keyIndex,
            exitBalance: exitBalance,
            slashingPenalty: slashingPenalty,
            isSlashed: isSlashed
        });
    }

    function _infos(WithdrawnValidatorInfo memory single)
        private
        pure
        returns (WithdrawnValidatorInfo[] memory infos)
    {
        infos = new WithdrawnValidatorInfo[](1);
        infos[0] = single;
    }

    function _infos(WithdrawnValidatorInfo memory first, WithdrawnValidatorInfo memory second)
        private
        pure
        returns (WithdrawnValidatorInfo[] memory infos)
    {
        infos = new WithdrawnValidatorInfo[](2);
        infos[0] = first;
        infos[1] = second;
    }

    function _assertInfosEq(
        WithdrawnValidatorInfo[] memory actual,
        WithdrawnValidatorInfo[] memory expected
    ) private pure {
        assertEq(actual.length, expected.length, "Unexpected length of the decoded list");

        for (uint256 i; i < expected.length; ++i) {
            assertEq(actual[i].nodeOperatorId, expected[i].nodeOperatorId, "nodeOperatorId");
            assertEq(actual[i].keyIndex, expected[i].keyIndex, "keyIndex");
            assertEq(actual[i].exitBalance, expected[i].exitBalance, "exitBalance");
            assertEq(actual[i].slashingPenalty, expected[i].slashingPenalty, "slashingPenalty");
            assertEq(actual[i].isSlashed, expected[i].isSlashed, "isSlashed");
        }
    }

    /// @dev python: encode_call_script of one module.reportSlashedWithdrawnValidators(values)
    function _reportSlashedWithdrawnValidatorsScript(WithdrawnValidatorInfo[] memory infos)
        private
        view
        returns (bytes memory)
    {
        return EVMScripts.encodeCallScript(
            address(baseModuleStub),
            abi.encodeWithSelector(IBaseModule.reportSlashedWithdrawnValidators.selector, infos)
        );
    }
}
