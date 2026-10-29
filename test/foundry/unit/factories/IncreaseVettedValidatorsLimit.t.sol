// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    IncreaseVettedValidatorsLimit
} from "contracts/EVMScriptFactories/IncreaseVettedValidatorsLimit.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Roles} from "test/foundry/unit/helpers/Roles.sol";

contract IncreaseVettedValidatorsLimitTest is Test {
    uint256 internal constant NODE_OPERATOR_ID = 0;
    uint256 internal constant NEW_STAKING_LIMIT = 1;
    uint256 internal constant TOO_HIGH_STAKING_LIMIT = 100000;
    uint64 internal constant SIGNING_KEYS_COUNT = 3;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal nodeOperatorManager = makeAddr("nodeOperatorManager");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistryStub;
    IncreaseVettedValidatorsLimit internal increaseVettedValidatorsLimit;

    function setUp() public {
        nodeOperatorsRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);

        vm.prank(owner);
        increaseVettedValidatorsLimit =
            new IncreaseVettedValidatorsLimit(address(nodeOperatorsRegistryStub));

        vm.label(address(nodeOperatorsRegistryStub), "nodeOperatorsRegistryStub");
        vm.label(address(increaseVettedValidatorsLimit), "increaseVettedValidatorsLimit");
    }

    function test_SetsInitialState() external view {
        assertEq(
            address(increaseVettedValidatorsLimit.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistryStub),
            "nodeOperatorsRegistry"
        );
    }

    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER");
        increaseVettedValidatorsLimit.createEVMScript(
            stranger, _encodeCallData(NODE_OPERATOR_ID, NEW_STAKING_LIMIT)
        );
    }

    function test_RevertWhen_NodeOperatorIsDisabled() external {
        nodeOperatorsRegistryStub.setActive(NODE_OPERATOR_ID, false);

        vm.expectRevert("NODE_OPERATOR_DISABLED");
        increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, NEW_STAKING_LIMIT)
        );
    }

    function test_RevertWhen_NotEnoughSigningKeys() external {
        vm.expectRevert("NOT_ENOUGH_SIGNING_KEYS");
        increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, TOO_HIGH_STAKING_LIMIT)
        );
    }

    function test_RevertWhen_StakingLimitIsTooLow() external {
        vm.expectRevert("STAKING_LIMIT_TOO_LOW");
        increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, 0)
        );
    }

    function test_CreatesEVMScriptFromRewardAddress() external {
        uint256 newStakingLimit = _addSigningKeys();

        bytes memory evmScript = increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, newStakingLimit)
        );

        assertEq(evmScript, _expectedEVMScript(newStakingLimit), "evmScript");
    }

    function test_CreatesEVMScriptFromManager() external {
        nodeOperatorsRegistryStub.setCanPerform(
            nodeOperatorManager, Roles.MANAGE_SIGNING_KEYS_ROLE, NODE_OPERATOR_ID, true
        );
        uint256 newStakingLimit = _addSigningKeys();

        bytes memory evmScript = increaseVettedValidatorsLimit.createEVMScript(
            nodeOperatorManager, _encodeCallData(NODE_OPERATOR_ID, newStakingLimit)
        );

        assertEq(evmScript, _expectedEVMScript(newStakingLimit), "evmScript");
    }

    function test_DecodesEVMScriptCallData() external view {
        IncreaseVettedValidatorsLimit.VettedValidatorsLimitInput memory input =
            increaseVettedValidatorsLimit.decodeEVMScriptCallData(
                _encodeCallData(NODE_OPERATOR_ID, NEW_STAKING_LIMIT)
            );

        assertEq(input.nodeOperatorId, NODE_OPERATOR_ID, "nodeOperatorId");
        assertEq(input.stakingLimit, NEW_STAKING_LIMIT, "stakingLimit");
    }

    /// @dev Adds signing keys to the operator and returns the staking limit that vets them
    function _addSigningKeys() private returns (uint256) {
        nodeOperatorsRegistryStub.setTotalSigningKeys(
            NODE_OPERATOR_ID, nodeOperatorsRegistryStub.totalSigningKeys() + SIGNING_KEYS_COUNT
        );
        return nodeOperatorsRegistryStub.stakingLimit() + SIGNING_KEYS_COUNT;
    }

    function _encodeCallData(uint256 nodeOperatorId, uint256 stakingLimit)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(nodeOperatorId, stakingLimit);
    }

    function _expectedEVMScript(uint256 stakingLimit) private view returns (bytes memory) {
        return EVMScripts.encodeCallScript(
            address(nodeOperatorsRegistryStub),
            abi.encodeWithSelector(
                INodeOperatorsRegistry.setNodeOperatorStakingLimit.selector,
                NODE_OPERATOR_ID,
                stakingLimit
            )
        );
    }
}
