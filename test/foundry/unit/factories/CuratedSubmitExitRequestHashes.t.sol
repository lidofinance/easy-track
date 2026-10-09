// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    CuratedSubmitExitRequestHashes
} from "contracts/EVMScriptFactories/CuratedSubmitExitRequestHashes.sol";
import {SubmitExitRequestHashesUtils} from "contracts/libraries/SubmitExitRequestHashesUtils.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {StakingRouterStub} from "contracts/test/StakingRouterStub.sol";
import {ValidatorExitBusOracleStub} from "contracts/test/ValidatorExitBusOracleStub.sol";
import {ExitRequests} from "test/foundry/unit/helpers/ExitRequests.sol";

contract CuratedSubmitExitRequestHashesTest is Test {
    uint256 internal constant CURATED_MODULE_ID = 1;
    uint256 internal constant NODE_OPERATOR_ID = 0;
    uint64 internal constant VALIDATOR_INDEX = 0;

    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    StakingRouterStub internal stakingRouterStub;
    ValidatorExitBusOracleStub internal validatorsExitBusOracleStub;
    NodeOperatorsRegistryStub internal curatedRegistryStub;
    CuratedSubmitExitRequestHashes internal curatedSubmitExitRequestHashes;

    function setUp() public {
        stakingRouterStub = new StakingRouterStub();
        validatorsExitBusOracleStub = new ValidatorExitBusOracleStub();

        curatedRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);
        stakingRouterStub.setStakingModule(CURATED_MODULE_ID, address(curatedRegistryStub));
        curatedRegistryStub.setSigningKeys(NODE_OPERATOR_ID, ExitRequests.concatenatedPubkeys());

        vm.prank(nodeOperator);
        curatedSubmitExitRequestHashes = new CuratedSubmitExitRequestHashes(
            address(curatedRegistryStub),
            address(stakingRouterStub),
            address(validatorsExitBusOracleStub)
        );

        vm.label(address(stakingRouterStub), "stakingRouterStub");
        vm.label(address(validatorsExitBusOracleStub), "validatorsExitBusOracleStub");
        vm.label(address(curatedRegistryStub), "curatedRegistryStub");
        vm.label(address(curatedSubmitExitRequestHashes), "curatedSubmitExitRequestHashes");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(
            address(curatedSubmitExitRequestHashes.stakingRouter()),
            address(stakingRouterStub),
            "stakingRouter"
        );
        assertEq(
            address(curatedSubmitExitRequestHashes.validatorsExitBusOracle()),
            address(validatorsExitBusOracleStub),
            "validatorsExitBusOracle"
        );
        assertEq(
            address(curatedSubmitExitRequestHashes.nodeOperatorsRegistry()),
            address(curatedRegistryStub),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_deploy_zero_staking_router
    function test_DeploysWithZeroStakingRouter() external {
        vm.prank(nodeOperator);
        CuratedSubmitExitRequestHashes curated = new CuratedSubmitExitRequestHashes(
            address(curatedRegistryStub), address(0), address(validatorsExitBusOracleStub)
        );

        assertEq(address(curated.stakingRouter()), address(0), "stakingRouter");
    }

    // python: test_deploy_zero_validators_exit_bus_oracle_stub
    function test_DeploysWithZeroValidatorsExitBusOracle() external {
        vm.prank(nodeOperator);
        CuratedSubmitExitRequestHashes curated = new CuratedSubmitExitRequestHashes(
            address(curatedRegistryStub), address(stakingRouterStub), address(0)
        );

        assertEq(address(curated.validatorsExitBusOracle()), address(0), "validatorsExitBusOracle");
    }

    // python: test_deploy_zero_node_operators_registry
    function test_DeploysWithZeroNodeOperatorsRegistry() external {
        vm.prank(nodeOperator);
        CuratedSubmitExitRequestHashes curated = new CuratedSubmitExitRequestHashes(
            address(0), address(stakingRouterStub), address(validatorsExitBusOracleStub)
        );

        assertEq(address(curated.nodeOperatorsRegistry()), address(0), "nodeOperatorsRegistry");
    }

    // python: test_only_node_operator_can_call_create_evm_script_wrong_caller
    function test_RevertWhen_CreatorIsNotNodeOperator() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests =
            new SubmitExitRequestHashesUtils.ExitRequestInput[](1);
        requests[0] = SubmitExitRequestHashesUtils.ExitRequestInput({
            moduleId: CURATED_MODULE_ID,
            nodeOpId: NODE_OPERATOR_ID,
            valIndex: VALIDATOR_INDEX,
            valPubkey: ExitRequests.pubkeyAt(0),
            valPubKeyIndex: 0
        });

        vm.prank(stranger);
        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR");
        curatedSubmitExitRequestHashes.createEVMScript(stranger, abi.encode(requests));
    }
}
