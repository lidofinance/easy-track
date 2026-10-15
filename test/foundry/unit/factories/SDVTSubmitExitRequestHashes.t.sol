// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SDVTSubmitExitRequestHashes
} from "contracts/EVMScriptFactories/SDVTSubmitExitRequestHashes.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {StakingRouterStub} from "contracts/test/StakingRouterStub.sol";
import {ValidatorExitBusOracleStub} from "contracts/test/ValidatorExitBusOracleStub.sol";

contract SDVTSubmitExitRequestHashesTest is Test {
    address internal owner = makeAddr("owner");
    address internal nodeOperator = makeAddr("nodeOperator");

    StakingRouterStub internal stakingRouterStub;
    ValidatorExitBusOracleStub internal validatorsExitBusOracleStub;
    NodeOperatorsRegistryStub internal sdvtRegistryStub;
    SDVTSubmitExitRequestHashes internal sdvtSubmitExitRequestHashes;

    function setUp() public {
        stakingRouterStub = new StakingRouterStub();
        validatorsExitBusOracleStub = new ValidatorExitBusOracleStub();
        sdvtRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);

        vm.prank(owner);
        sdvtSubmitExitRequestHashes = new SDVTSubmitExitRequestHashes(
            owner,
            address(sdvtRegistryStub),
            address(stakingRouterStub),
            address(validatorsExitBusOracleStub)
        );

        vm.label(address(stakingRouterStub), "stakingRouterStub");
        vm.label(address(validatorsExitBusOracleStub), "validatorsExitBusOracleStub");
        vm.label(address(sdvtRegistryStub), "sdvtRegistryStub");
        vm.label(address(sdvtSubmitExitRequestHashes), "sdvtSubmitExitRequestHashes");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(sdvtSubmitExitRequestHashes.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(sdvtSubmitExitRequestHashes.stakingRouter()),
            address(stakingRouterStub),
            "stakingRouter"
        );
        assertEq(
            address(sdvtSubmitExitRequestHashes.validatorsExitBusOracle()),
            address(validatorsExitBusOracleStub),
            "validatorsExitBusOracle"
        );
        assertEq(
            address(sdvtSubmitExitRequestHashes.nodeOperatorsRegistry()),
            address(sdvtRegistryStub),
            "nodeOperatorsRegistry"
        );
    }

    // python: test_deploy_zero_staking_router
    function test_DeploysWithZeroStakingRouter() external {
        vm.prank(owner);
        SDVTSubmitExitRequestHashes sdvt = new SDVTSubmitExitRequestHashes(
            owner, address(sdvtRegistryStub), address(0), address(validatorsExitBusOracleStub)
        );

        assertEq(address(sdvt.stakingRouter()), address(0), "stakingRouter");
    }

    // python: test_deploy_zero_validators_exit_bus_oracle_stub
    function test_DeploysWithZeroValidatorsExitBusOracle() external {
        vm.prank(owner);
        SDVTSubmitExitRequestHashes sdvt = new SDVTSubmitExitRequestHashes(
            owner, address(sdvtRegistryStub), address(stakingRouterStub), address(0)
        );

        assertEq(address(sdvt.validatorsExitBusOracle()), address(0), "validatorsExitBusOracle");
    }

    // python: test_deploy_zero_node_operators_registry
    function test_DeploysWithZeroNodeOperatorsRegistry() external {
        vm.prank(owner);
        SDVTSubmitExitRequestHashes sdvt = new SDVTSubmitExitRequestHashes(
            owner, address(0), address(stakingRouterStub), address(validatorsExitBusOracleStub)
        );

        assertEq(address(sdvt.nodeOperatorsRegistry()), address(0), "nodeOperatorsRegistry");
    }
}
