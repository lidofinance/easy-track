// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    RegisterTiersInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/RegisterTiersInOperatorGrid.sol";
import {IOperatorGrid, TierParams} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract RegisterTiersInOperatorGridTest is Test {
    /// @dev python: operator_address
    address internal constant OPERATOR = address(1);
    uint256 internal constant GROUP_SHARE_LIMIT = 1000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    /// @dev python: operator1 and operator2, accounts[5] and accounts[6]
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

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(registerTiersInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(registerTiersInOperatorGrid.lidoLocator()),
            address(lidoLocatorStub),
            "lidoLocator"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        registerTiersInOperatorGrid.createEVMScript(stranger, "");
    }

    // python: test_empty_node_operators_array
    function test_RevertWhen_NodeOperatorsAreEmpty() external {
        address[] memory nodeOperators = new address[](0);
        TierParams[][] memory tiers = new TierParams[][](1);

        vm.expectRevert("EMPTY_NODE_OPERATORS");
        registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(nodeOperators, tiers));
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        TierParams[][] memory tiers = new TierParams[][](2);

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(_operators(stranger), tiers));
    }

    // python: test_zero_node_operator
    function test_RevertWhen_NodeOperatorIsZero() external {
        TierParams[][] memory tiers = _tiers(
            _tierParams(Vaults.defaultTierParams()), _tierParams(Vaults.defaultTierParams())
        );

        vm.expectRevert("ZERO_NODE_OPERATOR");
        registerTiersInOperatorGrid.createEVMScript(
            owner, abi.encode(_operators(address(0), stranger), tiers)
        );
    }

    // python: test_empty_tiers_array
    function test_RevertWhen_TiersAreEmpty() external {
        _givenGroupRegistered(stranger, GROUP_SHARE_LIMIT);

        TierParams[][] memory tiers = new TierParams[][](1);

        vm.expectRevert("EMPTY_TIERS");
        registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(_operators(stranger), tiers));
    }

    // python: test_group_not_exists
    function test_RevertWhen_GroupDoesNotExist() external {
        vm.expectRevert("GROUP_NOT_EXISTS");
        registerTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(stranger, Vaults.defaultTierParams())
        );
    }

    // python: test_default_tier_operator
    function test_RevertWhen_NodeOperatorIsDefaultTierOperator() external {
        address defaultTierOperator = registerTiersInOperatorGrid.DEFAULT_TIER_OPERATOR();

        vm.expectRevert("DEFAULT_TIER_OPERATOR");
        registerTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(defaultTierOperator, Vaults.defaultTierParams())
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        _givenGroupRegistered(nodeOperator, 1000);
        _givenGroupRegistered(anotherNodeOperator, 1500);

        address[] memory nodeOperators = _operators(nodeOperator, anotherNodeOperator);
        TierParams[][] memory tiers = _tiers(
            _tierParams(Vaults.defaultTierParams()),
            _tierParams(Vaults.tierParams(800, 300, 150, 75, 60, 20))
        );

        bytes memory evmScript =
            registerTiersInOperatorGrid.createEVMScript(owner, abi.encode(nodeOperators, tiers));

        assertEq(evmScript, _registerTiersScript(nodeOperators, tiers), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory nodeOperators = _operators(nodeOperator, anotherNodeOperator);
        TierParams[][] memory tiers = _tiers(
            _tierParams(Vaults.defaultTierParams()),
            _tierParams(Vaults.tierParams(2000, 300, 150, 75, 60, 20))
        );

        (address[] memory decodedNodeOperators, TierParams[][] memory decodedTiers) =
            registerTiersInOperatorGrid.decodeEVMScriptCallData(abi.encode(nodeOperators, tiers));

        assertEq(decodedNodeOperators, nodeOperators, "nodeOperators");
        _assertTiersEq(decodedTiers, tiers);
    }

    // python: test_tier_share_limit_exceeds_group_share_limit
    function test_AllowsTierShareLimitAboveGroupShareLimit() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        // the group share limit is enforced by the operator grid at minting time, not here
        TierParams memory tier = Vaults.defaultTierParams();
        tier.shareLimit = 1500;

        bytes memory evmScript =
            registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    // python: test_tier_share_limit_too_high
    function test_RevertWhen_TierShareLimitIsTooHigh() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.shareLimit = Vaults.MAX_TIER_SHARE_LIMIT + 1;

        vm.expectRevert("TIER_SHARE_LIMIT_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_zero_reserve_ratio
    function test_RevertWhen_ReserveRatioIsZero() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.reserveRatioBP = 0;

        vm.expectRevert("ZERO_RESERVE_RATIO");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_reserve_ratio_too_high
    function test_RevertWhen_ReserveRatioIsTooHigh() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.reserveRatioBP = 10000;

        vm.expectRevert("RESERVE_RATIO_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_zero_forced_rebalance_threshold
    function test_RevertWhen_ForcedRebalanceThresholdIsZero() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 0;

        vm.expectRevert("ZERO_FORCED_REBALANCE_THRESHOLD");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_forced_rebalance_threshold_too_high
    function test_RevertWhen_ForcedRebalanceThresholdIsTooHigh() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 300;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_forced_rebalance_threshold_equals_reserve_ratio
    function test_RevertWhen_ForcedRebalanceThresholdEqualsReserveRatio() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = tier.reserveRatioBP;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_forced_rebalance_threshold_within_10bp_of_reserve_ratio
    function test_RevertWhen_ForcedRebalanceThresholdIsWithin10BPOfReserveRatio() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 191;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_forced_rebalance_threshold_exactly_10bp_below_reserve_ratio
    function test_AllowsForcedRebalanceThresholdExactly10BPBelowReserveRatio() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 189;

        bytes memory evmScript =
            registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    // python: test_infra_fee_too_high
    function test_RevertWhen_InfraFeeIsTooHigh() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.infraFeeBP = 70001;

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_liquidity_fee_too_high
    function test_RevertWhen_LiquidityFeeIsTooHigh() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.liquidityFeeBP = 70001;

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    // python: test_reservation_fee_too_high
    function test_RevertWhen_ReservationFeeIsTooHigh() external {
        _givenGroupRegistered(OPERATOR, GROUP_SHARE_LIMIT);

        TierParams memory tier = Vaults.defaultTierParams();
        tier.reservationFeeBP = 70001;

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        registerTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(OPERATOR, tier));
    }

    /// @dev python: operatorGrid.registerGroup(nodeOperator, shareLimit, {"from": owner})
    function _givenGroupRegistered(address operator, uint256 shareLimit) private {
        vm.prank(owner);
        operatorGrid.registerGroup(operator, shareLimit);
    }

    function _operators(address operator) private pure returns (address[] memory nodeOperators) {
        nodeOperators = new address[](1);
        nodeOperators[0] = operator;
    }

    function _operators(address first, address second)
        private
        pure
        returns (address[] memory nodeOperators)
    {
        nodeOperators = new address[](2);
        nodeOperators[0] = first;
        nodeOperators[1] = second;
    }

    function _tierParams(TierParams memory tier) private pure returns (TierParams[] memory list) {
        list = new TierParams[](1);
        list[0] = tier;
    }

    function _tiers(TierParams[] memory list) private pure returns (TierParams[][] memory tiers) {
        tiers = new TierParams[][](1);
        tiers[0] = list;
    }

    function _tiers(TierParams[] memory first, TierParams[] memory second)
        private
        pure
        returns (TierParams[][] memory tiers)
    {
        tiers = new TierParams[][](2);
        tiers[0] = first;
        tiers[1] = second;
    }

    /// @dev python: create_calldata([operator], [[tier]])
    function _encodeCallData(address operator, TierParams memory tier)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(_operators(operator), _tiers(_tierParams(tier)));
    }

    /// @dev python: encode_call_script of one registerTiers per operator, every call to the
    /// operator grid
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
            _assertTierParamsEq(actual[i], expected[i]);
        }
    }

    function _assertTierParamsEq(TierParams[] memory actual, TierParams[] memory expected)
        private
        pure
    {
        assertEq(actual.length, expected.length, "tierParams.length");

        for (uint256 i; i < actual.length; ++i) {
            assertEq(actual[i].shareLimit, expected[i].shareLimit, "shareLimit");
            assertEq(actual[i].reserveRatioBP, expected[i].reserveRatioBP, "reserveRatioBP");
            assertEq(
                actual[i].forcedRebalanceThresholdBP,
                expected[i].forcedRebalanceThresholdBP,
                "forcedRebalanceThresholdBP"
            );
            assertEq(actual[i].infraFeeBP, expected[i].infraFeeBP, "infraFeeBP");
            assertEq(actual[i].liquidityFeeBP, expected[i].liquidityFeeBP, "liquidityFeeBP");
            assertEq(actual[i].reservationFeeBP, expected[i].reservationFeeBP, "reservationFeeBP");
        }
    }
}
