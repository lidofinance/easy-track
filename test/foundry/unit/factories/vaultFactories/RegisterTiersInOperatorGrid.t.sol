// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    RegisterTiersInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/RegisterTiersInOperatorGrid.sol";
import {IOperatorGrid, TierParams} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract RegisterTiersInOperatorGridTest is Test {
    address internal constant OPERATOR = address(1);
    uint256 internal constant GROUP_SHARE_LIMIT = 1000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal anotherNodeOperator = makeAddr("anotherNodeOperator");

    LidoLocatorStub internal lidoLocatorStub;
    IOperatorGrid internal operatorGrid;
    RegisterTiersInOperatorGrid internal registerTiersInOperatorGrid;

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        operatorGrid = IOperatorGrid(lidoLocatorStub.operatorGrid());

        vm.prank(owner);
        registerTiersInOperatorGrid =
            new RegisterTiersInOperatorGrid(owner, address(lidoLocatorStub));

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(operatorGrid), "operatorGridStub");
        vm.label(address(registerTiersInOperatorGrid), "registerTiersInOperatorGrid");
    }

    function test_SetsInitialState() external view {
        assertEq(registerTiersInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(registerTiersInOperatorGrid.lidoLocator()),
            address(lidoLocatorStub),
            "lidoLocator"
        );
    }

    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        registerTiersInOperatorGrid.createEVMScript(stranger, "");
    }

    function test_RevertWhen_NodeOperatorsAreEmpty() external {
        address[] memory nodeOperators = new address[](0);
        TierParams[][] memory tiers = new TierParams[][](1);

        vm.expectRevert("EMPTY_NODE_OPERATORS");
        registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(nodeOperators, tiers));
    }

    function test_RevertWhen_ArrayLengthsMismatch() external {
        TierParams[][] memory tiers = new TierParams[][](2);

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(Arrays.list(stranger), tiers));
    }

    function test_RevertWhen_NodeOperatorIsZero() external {
        TierParams[][] memory tiers = Arrays.list(
            Arrays.list(Vaults.defaultTierParams()), Arrays.list(Vaults.defaultTierParams())
        );

        vm.expectRevert("ZERO_NODE_OPERATOR");
        registerTiersInOperatorGrid.createEVMScript(
            owner, abi.encode(Arrays.list(address(0), stranger), tiers)
        );
    }

    function test_RevertWhen_TiersAreEmpty() external {
        _registerGroup(stranger, GROUP_SHARE_LIMIT);

        TierParams[][] memory tiers = new TierParams[][](1);

        vm.expectRevert("EMPTY_TIERS");
        registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(Arrays.list(stranger), tiers));
    }

    function test_RevertWhen_GroupDoesNotExist() external {
        vm.expectRevert("GROUP_NOT_EXISTS");
        registerTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(stranger, Vaults.defaultTierParams())
        );
    }

    function test_RevertWhen_NodeOperatorIsDefaultTierOperator() external {
        address defaultTierOperator = registerTiersInOperatorGrid.DEFAULT_TIER_OPERATOR();

        vm.expectRevert("DEFAULT_TIER_OPERATOR");
        registerTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(defaultTierOperator, Vaults.defaultTierParams())
        );
    }

    function test_CreatesEVMScript() external {
        _registerGroup(nodeOperator, 1000);
        _registerGroup(anotherNodeOperator, 1500);

        address[] memory nodeOperators = Arrays.list(nodeOperator, anotherNodeOperator);
        TierParams[][] memory tiers = Arrays.list(
            Arrays.list(Vaults.defaultTierParams()),
            Arrays.list(Vaults.tierParams(800, 300, 150, 75, 60, 20))
        );

        bytes memory evmScript =
            registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(nodeOperators, tiers));

        assertEq(evmScript, _registerTiersScript(nodeOperators, tiers), "evmScript");
    }

    function test_DecodesEVMScriptCallData() external view {
        address[] memory nodeOperators = Arrays.list(nodeOperator, anotherNodeOperator);
        TierParams[][] memory tiers = Arrays.list(
            Arrays.list(Vaults.defaultTierParams()),
            Arrays.list(Vaults.tierParams(2000, 300, 150, 75, 60, 20))
        );

        (address[] memory decodedNodeOperators, TierParams[][] memory decodedTiers) =
            registerTiersInOperatorGrid.decodeEVMScriptCallData(abi.encode(nodeOperators, tiers));

        assertEq(decodedNodeOperators, nodeOperators, "nodeOperators");
        _assertTiersEq(decodedTiers, tiers);
    }

    function test_AllowsTierShareLimitAboveGroupShareLimit() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        // the group share limit is enforced by the operator grid at minting time, not here
        TierParams memory tier = Vaults.defaultTierParams();
        tier.shareLimit = 1500;

        bytes memory evmScript =
            registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    function test_RevertWhen_TierShareLimitIsTooHigh() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.shareLimit = Vaults.MAX_TIER_SHARE_LIMIT + 1;

        vm.expectRevert("TIER_SHARE_LIMIT_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_ReserveRatioIsZero() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.reserveRatioBP = 0;

        vm.expectRevert("ZERO_RESERVE_RATIO");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_ReserveRatioIsTooHigh() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.reserveRatioBP = 10000;

        vm.expectRevert("RESERVE_RATIO_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_ForcedRebalanceThresholdIsZero() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 0;

        vm.expectRevert("ZERO_FORCED_REBALANCE_THRESHOLD");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_ForcedRebalanceThresholdIsTooHigh() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 300;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_ForcedRebalanceThresholdEqualsReserveRatio() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = tier.reserveRatioBP;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_ForcedRebalanceThresholdIsWithin10BPOfReserveRatio() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 191;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_AllowsForcedRebalanceThresholdExactly10BPBelowReserveRatio() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 189;

        bytes memory evmScript =
            registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    function test_RevertWhen_InfraFeeIsTooHigh() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.infraFeeBP = 70001;

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_LiquidityFeeIsTooHigh() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.liquidityFeeBP = 70001;

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function test_RevertWhen_ReservationFeeIsTooHigh() external {
        _registerGroup(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.reservationFeeBP = 70001;

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    function _registerGroup(address operator, uint256 shareLimit) private {
        vm.prank(owner);
        operatorGrid.registerGroup(operator, shareLimit);
    }

    function _encodeCallData(address operator, TierParams memory tier)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(Arrays.list(operator), Arrays.list(Arrays.list(tier)));
    }

    function _registerTiersScript(address[] memory nodeOperators, TierParams[][] memory tiers)
        private
        view
        returns (bytes memory)
    {
        bytes[] memory calls = new bytes[](nodeOperators.length);

        for (uint256 i; i < nodeOperators.length; ++i) {
            calls[i] = abi.encodeWithSelector(
                IOperatorGrid.registerTiers.selector, nodeOperators[i], tiers[i]
            );
        }

        return EVMScripts.encodeCallScript(address(operatorGrid), calls);
    }

    function _assertTiersEq(TierParams[][] memory actual, TierParams[][] memory expected)
        private
        pure
    {
        assertEq(actual.length, expected.length, "tiers.length");

        for (uint256 i; i < actual.length; ++i) {
            Vaults.assertTierParamsEq(actual[i], expected[i]);
        }
    }
}
