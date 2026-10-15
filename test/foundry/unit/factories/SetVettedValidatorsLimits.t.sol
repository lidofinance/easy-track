// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SetVettedValidatorsLimits
} from "contracts/EVMScriptFactories/SetVettedValidatorsLimits.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract SetVettedValidatorsLimitsTest is Test {
    uint256 internal constant NODE_OPERATORS_COUNT = 2;
    uint256 internal constant NEW_STAKING_LIMIT = 1;
    uint256 internal constant TOO_HIGH_STAKING_LIMIT = 100000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistry;
    SetVettedValidatorsLimits internal setVettedValidatorsLimits;

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
        setVettedValidatorsLimits =
            new SetVettedValidatorsLimits(owner, address(nodeOperatorsRegistry));

        vm.label(address(nodeOperatorsRegistry), "nodeOperatorsRegistry");
        vm.label(address(setVettedValidatorsLimits), "setVettedValidatorsLimits");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(setVettedValidatorsLimits.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(setVettedValidatorsLimits.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistry),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        setVettedValidatorsLimits.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_CalldataIsEmpty() external {
        vm.expectRevert("EMPTY_CALLDATA");
        setVettedValidatorsLimits.createEVMScript(
            owner, _encodeCallData(new SetVettedValidatorsLimits.VettedValidatorsLimitInput[](0))
        );
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreNotSorted() external {
        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        setVettedValidatorsLimits.createEVMScript(owner, _encodeCallData(_inputs(1, 1, 0, 2)));

        vm.expectRevert("NODE_OPERATORS_IS_NOT_SORTED");
        setVettedValidatorsLimits.createEVMScript(owner, _encodeCallData(_inputs(0, 1, 0, 2)));
    }

    // python: test_non_active_operator_calldata
    function test_RevertWhen_NodeOperatorIsNotActive() external {
        nodeOperatorsRegistry.setActive(0, false);

        vm.expectRevert("NODE_OPERATOR_IS_NOT_ACTIVE");
        setVettedValidatorsLimits.createEVMScript(
            owner, _encodeCallData(_inputs(0, NEW_STAKING_LIMIT, 1, NEW_STAKING_LIMIT))
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_INDEX_OUT_OF_RANGE");
        setVettedValidatorsLimits.createEVMScript(
            owner, _encodeCallData(_inputs(nodeOperatorsCount, NEW_STAKING_LIMIT))
        );
    }

    // python: test_revert_on_not_enough_signing_keys
    function test_RevertWhen_NotEnoughSigningKeys() external {
        vm.expectRevert("NOT_ENOUGH_SIGNING_KEYS");
        setVettedValidatorsLimits.createEVMScript(
            owner, _encodeCallData(_inputs(0, TOO_HIGH_STAKING_LIMIT))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = setVettedValidatorsLimits.createEVMScript(
            owner, _encodeCallData(_inputs(0, NEW_STAKING_LIMIT, 1, NEW_STAKING_LIMIT))
        );

        address[] memory targets = new address[](2);
        targets[0] = address(nodeOperatorsRegistry);
        targets[1] = address(nodeOperatorsRegistry);

        bytes[] memory datas = new bytes[](2);
        datas[0] = _encodeSetNodeOperatorStakingLimit(0, NEW_STAKING_LIMIT);
        datas[1] = _encodeSetNodeOperatorStakingLimit(1, NEW_STAKING_LIMIT);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        SetVettedValidatorsLimits.VettedValidatorsLimitInput[] memory inputs =
            setVettedValidatorsLimits.decodeEVMScriptCallData(
                _encodeCallData(_inputs(0, NEW_STAKING_LIMIT, 1, NEW_STAKING_LIMIT))
            );

        assertEq(inputs.length, 2, "inputs length");
        assertEq(inputs[0].nodeOperatorId, 0, "inputs[0].nodeOperatorId");
        assertEq(inputs[0].stakingLimit, NEW_STAKING_LIMIT, "inputs[0].stakingLimit");
        assertEq(inputs[1].nodeOperatorId, 1, "inputs[1].nodeOperatorId");
        assertEq(inputs[1].stakingLimit, NEW_STAKING_LIMIT, "inputs[1].stakingLimit");
    }

    function _inputs(uint256 nodeOperatorId, uint256 stakingLimit)
        private
        pure
        returns (SetVettedValidatorsLimits.VettedValidatorsLimitInput[] memory inputs)
    {
        inputs = new SetVettedValidatorsLimits.VettedValidatorsLimitInput[](1);
        inputs[0] =
            SetVettedValidatorsLimits.VettedValidatorsLimitInput(nodeOperatorId, stakingLimit);
    }

    function _inputs(
        uint256 firstId,
        uint256 firstStakingLimit,
        uint256 secondId,
        uint256 secondStakingLimit
    ) private pure returns (SetVettedValidatorsLimits.VettedValidatorsLimitInput[] memory inputs) {
        inputs = new SetVettedValidatorsLimits.VettedValidatorsLimitInput[](2);
        inputs[0] = SetVettedValidatorsLimits.VettedValidatorsLimitInput(firstId, firstStakingLimit);
        inputs[1] =
            SetVettedValidatorsLimits.VettedValidatorsLimitInput(secondId, secondStakingLimit);
    }

    function _encodeCallData(SetVettedValidatorsLimits.VettedValidatorsLimitInput[] memory inputs)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(inputs);
    }

    function _encodeSetNodeOperatorStakingLimit(uint256 nodeOperatorId, uint256 stakingLimit)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            INodeOperatorsRegistry.setNodeOperatorStakingLimit.selector,
            nodeOperatorId,
            stakingLimit
        );
    }
}
