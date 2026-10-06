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

contract IncreaseVettedValidatorsLimitTest is Test {
    uint256 internal constant NODE_OPERATOR_ID = 0;
    uint256 internal constant NEW_STAKING_LIMIT = 1;
    uint256 internal constant TOO_HIGH_STAKING_LIMIT = 100000;
    /// @dev python: the three signing keys `addSigningKeysOperatorBH` adds before the limit is raised
    uint64 internal constant SIGNING_KEYS_COUNT = 3;
    bytes32 internal constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

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

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(
            address(increaseVettedValidatorsLimit.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistryStub),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER");
        increaseVettedValidatorsLimit.createEVMScript(
            stranger, _encodeCallData(NODE_OPERATOR_ID, NEW_STAKING_LIMIT)
        );
    }

    // python: test_create_evm_script_called_when_operator_disabled
    function test_RevertWhen_NodeOperatorIsDisabled() external {
        nodeOperatorsRegistryStub.setActive(NODE_OPERATOR_ID, false);

        vm.expectRevert("NODE_OPERATOR_DISABLED");
        increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, NEW_STAKING_LIMIT)
        );
    }

    // python: test_revert_on_not_enough_signing_keys
    function test_RevertWhen_NotEnoughSigningKeys() external {
        vm.expectRevert("NOT_ENOUGH_SIGNING_KEYS");
        increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, TOO_HIGH_STAKING_LIMIT)
        );
    }

    // python: test_revert_on_new_value_is_too_low
    function test_RevertWhen_StakingLimitIsTooLow() external {
        vm.expectRevert("STAKING_LIMIT_TOO_LOW");
        increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, 0)
        );
    }

    // python: test_create_evm_script_from_reward_address
    function test_CreatesEVMScriptFromRewardAddress() external {
        uint256 newStakingLimit = _givenSigningKeysAdded();

        bytes memory evmScript = increaseVettedValidatorsLimit.createEVMScript(
            nodeOperator, _encodeCallData(NODE_OPERATOR_ID, newStakingLimit)
        );

        assertEq(evmScript, _expectedEVMScript(newStakingLimit), "evmScript");
    }

    // python: test_create_evm_script_from_manager
    function test_CreatesEVMScriptFromManager() external {
        nodeOperatorsRegistryStub.setCanPerform(
            nodeOperatorManager, MANAGE_SIGNING_KEYS_ROLE, NODE_OPERATOR_ID, true
        );
        uint256 newStakingLimit = _givenSigningKeysAdded();

        bytes memory evmScript = increaseVettedValidatorsLimit.createEVMScript(
            nodeOperatorManager, _encodeCallData(NODE_OPERATOR_ID, newStakingLimit)
        );

        assertEq(evmScript, _expectedEVMScript(newStakingLimit), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        IncreaseVettedValidatorsLimit.VettedValidatorsLimitInput memory input =
            increaseVettedValidatorsLimit.decodeEVMScriptCallData(
                _encodeCallData(NODE_OPERATOR_ID, NEW_STAKING_LIMIT)
            );

        assertEq(input.nodeOperatorId, NODE_OPERATOR_ID, "nodeOperatorId");
        assertEq(input.stakingLimit, NEW_STAKING_LIMIT, "stakingLimit");
    }

    /// @dev python: addSigningKeysOperatorBH(0, 3, pubkeys, signatures). Returns the staking limit
    /// that vets the added keys
    function _givenSigningKeysAdded() private returns (uint256) {
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
