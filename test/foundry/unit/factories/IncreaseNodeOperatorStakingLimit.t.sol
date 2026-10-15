// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    IncreaseNodeOperatorStakingLimit
} from "contracts/EVMScriptFactories/IncreaseNodeOperatorStakingLimit.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract IncreaseNodeOperatorStakingLimitTest is Test {
    uint256 internal constant NODE_OPERATOR_ID = 0;
    uint256 internal constant STAKING_LIMIT = 350;
    uint64 internal constant STAKING_LIMIT_ABOVE_NEW = 370;
    uint64 internal constant TOTAL_SIGNING_KEYS_BELOW_NEW = 300;

    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    NodeOperatorsRegistryStub internal nodeOperatorsRegistryStub;
    IncreaseNodeOperatorStakingLimit internal increaseNodeOperatorStakingLimit;

    function setUp() public {
        nodeOperatorsRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);
        increaseNodeOperatorStakingLimit =
            new IncreaseNodeOperatorStakingLimit(address(nodeOperatorsRegistryStub));

        vm.label(address(nodeOperatorsRegistryStub), "nodeOperatorsRegistryStub");
        vm.label(address(increaseNodeOperatorStakingLimit), "increaseNodeOperatorStakingLimit");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(
            address(increaseNodeOperatorStakingLimit.nodeOperatorsRegistry()),
            address(nodeOperatorsRegistryStub),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_create_evm_script_different_reward_address
    function test_RevertWhen_CreatorIsNotNodeOperator() external {
        vm.expectRevert("CALLER_IS_NOT_NODE_OPERATOR");
        increaseNodeOperatorStakingLimit.createEVMScript(stranger, _encodeCallData());
    }

    // python: test_create_evm_script_node_operator_disabled
    function test_RevertWhen_NodeOperatorIsDisabled() external {
        nodeOperatorsRegistryStub.setActive(NODE_OPERATOR_ID, false);

        vm.expectRevert("NODE_OPERATOR_DISABLED");
        increaseNodeOperatorStakingLimit.createEVMScript(nodeOperator, _encodeCallData());
    }

    // python: test_create_evm_script_new_staking_limit_too_low
    function test_RevertWhen_StakingLimitIsTooLow() external {
        nodeOperatorsRegistryStub.setStakingLimit(NODE_OPERATOR_ID, STAKING_LIMIT_ABOVE_NEW);
        assertEq(nodeOperatorsRegistryStub.stakingLimit(), STAKING_LIMIT_ABOVE_NEW, "stakingLimit");

        vm.expectRevert("STAKING_LIMIT_TOO_LOW");
        increaseNodeOperatorStakingLimit.createEVMScript(nodeOperator, _encodeCallData());
    }

    // python: test_create_evm_script_new_staking_limit_less_than_total_signing_keys
    function test_RevertWhen_NotEnoughSigningKeys() external {
        nodeOperatorsRegistryStub.setTotalSigningKeys(
            NODE_OPERATOR_ID, TOTAL_SIGNING_KEYS_BELOW_NEW
        );
        assertEq(
            nodeOperatorsRegistryStub.totalSigningKeys(),
            TOTAL_SIGNING_KEYS_BELOW_NEW,
            "totalSigningKeys"
        );

        vm.expectRevert("NOT_ENOUGH_SIGNING_KEYS");
        increaseNodeOperatorStakingLimit.createEVMScript(nodeOperator, _encodeCallData());
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes memory evmScript =
            increaseNodeOperatorStakingLimit.createEVMScript(nodeOperator, _encodeCallData());

        assertEq(
            evmScript,
            EVMScripts.encodeCallScript(
                address(nodeOperatorsRegistryStub),
                abi.encodeWithSelector(
                    NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector,
                    NODE_OPERATOR_ID,
                    STAKING_LIMIT
                )
            ),
            "evmScript"
        );
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        (uint256 nodeOperatorId, uint256 stakingLimit) =
            increaseNodeOperatorStakingLimit.decodeEVMScriptCallData(_encodeCallData());

        assertEq(nodeOperatorId, NODE_OPERATOR_ID, "nodeOperatorId");
        assertEq(stakingLimit, STAKING_LIMIT, "stakingLimit");
    }

    /// @dev python: CALLDATA
    function _encodeCallData() private pure returns (bytes memory) {
        return abi.encode(NODE_OPERATOR_ID, STAKING_LIMIT);
    }
}
