// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    UpdateTargetValidatorLimits
} from "contracts/EVMScriptFactories/UpdateTargetValidatorLimits.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract UpdateTargetValidatorLimitsTest is Test {
    uint256 internal constant NODE_OPERATORS_COUNT = 2;
    uint256 internal constant TARGET_LIMIT_MODE = 1;
    uint256 internal constant TARGET_LIMIT = 1;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    UpdateTargetValidatorLimits internal updateTargetValidatorLimits;

    function setUp() public {
        nodeOperatorsRegistry = new NodeOperatorsRegistryStub(nodeOperator);

        for (uint256 i = 1; i < NODE_OPERATORS_COUNT; ++i) {
            nodeOperatorsRegistry.addNodeOperator(
                string(abi.encodePacked("Node Operator ", vm.toString(i))),
                nodeOperator,
                nodeOperatorsRegistry.stakingLimit(),
                nodeOperatorsRegistry.totalSigningKeys()
            );
        }

        vm.prank(owner);
        updateTargetValidatorLimits =
            new UpdateTargetValidatorLimits(owner, address(nodeOperatorsRegistry));

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(updateTargetValidatorLimits), "updateTargetValidatorLimits");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(updateTargetValidatorLimits.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(updateTargetValidatorLimits.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        updateTargetValidatorLimits.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        updateTargetValidatorLimits.createEVMScript(
            owner, _encodeCallData(new UpdateTargetValidatorLimits.TargetValidatorsLimit[](0))
        );
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreNotSorted() external {
        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        updateTargetValidatorLimits.createEVMScript(
            owner, _encodeCallData(_inputs(1, 1, 1, 0, 0, 2))
        );

        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        updateTargetValidatorLimits.createEVMScript(
            owner, _encodeCallData(_inputs(0, 1, 1, 0, 1, 2))
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_INDEX_OUT_OF_RANGE");
        updateTargetValidatorLimits.createEVMScript(
            owner, _encodeCallData(_inputs(nodeOperatorsCount, TARGET_LIMIT_MODE, TARGET_LIMIT))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = updateTargetValidatorLimits.createEVMScript(
            owner,
            _encodeCallData(
                _inputs(0, TARGET_LIMIT_MODE, TARGET_LIMIT, 1, TARGET_LIMIT_MODE, TARGET_LIMIT)
            )
        );

        address[] memory targets = new address[](2);
        targets[0] = address(nodeOperatorsRegistry);
        targets[1] = address(nodeOperatorsRegistry);

        bytes[] memory datas = new bytes[](2);
        datas[0] = _encodeUpdateTargetValidatorsLimits(0);
        datas[1] = _encodeUpdateTargetValidatorsLimits(1);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        UpdateTargetValidatorLimits.TargetValidatorsLimit[] memory inputs =
            updateTargetValidatorLimits.decodeEVMScriptCallData(
                _encodeCallData(
                    _inputs(0, TARGET_LIMIT_MODE, TARGET_LIMIT, 1, TARGET_LIMIT_MODE, TARGET_LIMIT)
                )
            );

        assertEq(inputs.length, 2, "inputs length");
        assertEq(inputs[0].nodeOperatorId, 0, "inputs[0].nodeOperatorId");
        assertEq(inputs[0].targetLimitMode, TARGET_LIMIT_MODE, "inputs[0].targetLimitMode");
        assertEq(inputs[0].targetLimit, TARGET_LIMIT, "inputs[0].targetLimit");
        assertEq(inputs[1].nodeOperatorId, 1, "inputs[1].nodeOperatorId");
        assertEq(inputs[1].targetLimitMode, TARGET_LIMIT_MODE, "inputs[1].targetLimitMode");
        assertEq(inputs[1].targetLimit, TARGET_LIMIT, "inputs[1].targetLimit");
    }

    function _inputs(uint256 nodeOperatorId, uint256 targetLimitMode, uint256 targetLimit)
        private
        pure
        returns (UpdateTargetValidatorLimits.TargetValidatorsLimit[] memory inputs)
    {
        inputs = new UpdateTargetValidatorLimits.TargetValidatorsLimit[](1);
        inputs[0] = UpdateTargetValidatorLimits.TargetValidatorsLimit(
            nodeOperatorId, targetLimitMode, targetLimit
        );
    }

    function _inputs(
        uint256 firstId,
        uint256 firstTargetLimitMode,
        uint256 firstTargetLimit,
        uint256 secondId,
        uint256 secondTargetLimitMode,
        uint256 secondTargetLimit
    ) private pure returns (UpdateTargetValidatorLimits.TargetValidatorsLimit[] memory inputs) {
        inputs = new UpdateTargetValidatorLimits.TargetValidatorsLimit[](2);
        inputs[0] = UpdateTargetValidatorLimits.TargetValidatorsLimit(
            firstId, firstTargetLimitMode, firstTargetLimit
        );
        inputs[1] = UpdateTargetValidatorLimits.TargetValidatorsLimit(
            secondId, secondTargetLimitMode, secondTargetLimit
        );
    }

    function _encodeCallData(UpdateTargetValidatorLimits.TargetValidatorsLimit[] memory inputs)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(inputs);
    }

    function _encodeUpdateTargetValidatorsLimits(uint256 nodeOperatorId)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            INodeOperatorsRegistry.updateTargetValidatorsLimits.selector,
            nodeOperatorId,
            TARGET_LIMIT_MODE,
            TARGET_LIMIT
        );
    }
}
