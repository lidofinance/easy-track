// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    RegisterGroupsInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/RegisterGroupsInOperatorGrid.sol";
import {IOperatorGrid, TierParams} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract RegisterGroupsInOperatorGridTest is Test {
    /// @dev The maxShareLimit constructor argument
    uint256 internal constant MAX_SHARE_LIMIT = 10000;
    /// @dev python: operator1 and operator2, in ascending order
    address internal constant FIRST_OPERATOR = address(1);
    address internal constant SECOND_OPERATOR = address(2);
    uint256 internal constant GROUP_SHARE_LIMIT = 1000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    LidoLocatorStub internal lidoLocatorStub;
    IOperatorGrid internal operatorGrid;
    RegisterGroupsInOperatorGrid internal registerGroupsInOperatorGrid;

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        operatorGrid = IOperatorGrid(lidoLocatorStub.operatorGrid());

        vm.prank(owner);
        registerGroupsInOperatorGrid =
            new RegisterGroupsInOperatorGrid(owner, address(lidoLocatorStub), MAX_SHARE_LIMIT);

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(operatorGrid), "operatorGridStub");
        vm.label(address(registerGroupsInOperatorGrid), "registerGroupsInOperatorGrid");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(registerGroupsInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(registerGroupsInOperatorGrid.lidoLocator()),
            address(lidoLocatorStub),
            "lidoLocator"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        registerGroupsInOperatorGrid.createEVMScript(stranger, "");
    }

    // python: test_empty_node_operators_array
    function test_RevertWhen_NodeOperatorsAreEmpty() external {
        address[] memory nodeOperators = new address[](0);
        uint256[] memory shareLimits = new uint256[](0);
        TierParams[][] memory tiers = new TierParams[][](1);

        vm.expectRevert("EMPTY_NODE_OPERATORS");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, abi.encode(nodeOperators, shareLimits, tiers)
        );
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        TierParams[][] memory tiers = new TierParams[][](2);

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, abi.encode(_operators(stranger), _shareLimits(GROUP_SHARE_LIMIT), tiers)
        );
    }

    // python: test_zero_node_operator
    function test_RevertWhen_NodeOperatorIsZero() external {
        vm.expectRevert("ZERO_NODE_OPERATOR");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodePairCallData(address(0), stranger)
        );
    }

    // python: test_default_tier_operator
    function test_RevertWhen_NodeOperatorIsDefaultTierOperator() external {
        address defaultTierOperator = registerGroupsInOperatorGrid.DEFAULT_TIER_OPERATOR();

        vm.expectRevert("DEFAULT_TIER_OPERATOR");
        registerGroupsInOperatorGrid.createEVMScript(
            owner,
            _encodeCallData(defaultTierOperator, GROUP_SHARE_LIMIT, Vaults.defaultTierParams())
        );
    }

    // python: test_empty_tiers_array
    function test_RevertWhen_TiersAreEmpty() external {
        TierParams[][] memory tiers = new TierParams[][](1);

        vm.expectRevert("EMPTY_TIERS");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, abi.encode(_operators(FIRST_OPERATOR), _shareLimits(GROUP_SHARE_LIMIT), tiers)
        );
    }

    // python: test_group_exists
    function test_RevertWhen_GroupExists() external {
        _registerGroup(stranger, GROUP_SHARE_LIMIT);

        vm.expectRevert("GROUP_EXISTS");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(stranger, GROUP_SHARE_LIMIT, Vaults.defaultTierParams())
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        address[] memory nodeOperators = _operators(FIRST_OPERATOR, SECOND_OPERATOR);
        uint256[] memory shareLimits = _shareLimits(1000, 3000);
        TierParams[][] memory tiers = _tiers(
            _tierParams(Vaults.defaultTierParams()),
            _tierParams(Vaults.tierParams(2000, 300, 150, 75, 60, 20))
        );

        bytes memory evmScript = registerGroupsInOperatorGrid.createEVMScript(
            owner, abi.encode(nodeOperators, shareLimits, tiers)
        );

        assertEq(evmScript, _registerGroupsScript(nodeOperators, shareLimits, tiers), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory nodeOperators = _operators(FIRST_OPERATOR, SECOND_OPERATOR);
        uint256[] memory shareLimits = _shareLimits(1000, 1500);
        TierParams[][] memory tiers = _tiers(
            _tierParams(Vaults.defaultTierParams()),
            _tierParams(Vaults.tierParams(2000, 300, 150, 75, 60, 20))
        );

        (
            address[] memory decodedNodeOperators,
            uint256[] memory decodedShareLimits,
            TierParams[][] memory decodedTiers
        ) = registerGroupsInOperatorGrid.decodeEVMScriptCallData(
                abi.encode(nodeOperators, shareLimits, tiers)
            );

        assertEq(decodedNodeOperators, nodeOperators, "nodeOperators");
        assertEq(decodedShareLimits, shareLimits, "shareLimits");
        _assertTiersEq(decodedTiers, tiers);
    }

    // python: test_tier_share_limit_exceeds_group_share_limit
    function test_AllowsTierShareLimitAboveGroupShareLimit() external view {
        // the group share limit is enforced by the operator grid at minting time, not here
        TierParams memory tier = Vaults.defaultTierParams();
        tier.shareLimit = 1500;

        bytes memory evmScript = registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    // python: test_tier_share_limit_too_high
    function test_RevertWhen_TierShareLimitIsTooHigh() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.shareLimit = Vaults.MAX_TIER_SHARE_LIMIT + 1;

        vm.expectRevert("TIER_SHARE_LIMIT_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_group_share_limit_too_high
    function test_RevertWhen_GroupShareLimitIsTooHigh() external {
        uint256 shareLimit = registerGroupsInOperatorGrid.maxShareLimit() + 1;

        vm.expectRevert("GROUP_SHARE_LIMIT_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, shareLimit, Vaults.defaultTierParams())
        );
    }

    // python: test_ascending_order_in_operators_array_duplicate
    function test_RevertWhen_NodeOperatorsHaveDuplicate() external {
        vm.expectRevert("ASCENDING_ORDER_IN_OPERATORS_ARRAY");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodePairCallData(FIRST_OPERATOR, FIRST_OPERATOR)
        );
    }

    // python: test_ascending_order_in_operators_array_wrong_order
    function test_RevertWhen_NodeOperatorsAreNotAscending() external {
        vm.expectRevert("ASCENDING_ORDER_IN_OPERATORS_ARRAY");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodePairCallData(SECOND_OPERATOR, FIRST_OPERATOR)
        );
    }

    // python: test_correct_ascending_order_in_operators_array
    function test_AllowsAscendingNodeOperators() external view {
        bytes memory evmScript = registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodePairCallData(FIRST_OPERATOR, SECOND_OPERATOR)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    // python: test_zero_reserve_ratio
    function test_RevertWhen_ReserveRatioIsZero() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.reserveRatioBP = 0;

        vm.expectRevert("ZERO_RESERVE_RATIO");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_reserve_ratio_too_high
    function test_RevertWhen_ReserveRatioIsTooHigh() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.reserveRatioBP = 10000;

        vm.expectRevert("RESERVE_RATIO_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_zero_forced_rebalance_threshold
    function test_RevertWhen_ForcedRebalanceThresholdIsZero() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 0;

        vm.expectRevert("ZERO_FORCED_REBALANCE_THRESHOLD");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_forced_rebalance_threshold_too_high
    function test_RevertWhen_ForcedRebalanceThresholdIsTooHigh() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 300;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_forced_rebalance_threshold_equals_reserve_ratio
    function test_RevertWhen_ForcedRebalanceThresholdEqualsReserveRatio() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = tier.reserveRatioBP;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_forced_rebalance_threshold_within_10bp_of_reserve_ratio
    function test_RevertWhen_ForcedRebalanceThresholdIsWithin10BPOfReserveRatio() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 191;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_forced_rebalance_threshold_exactly_10bp_below_reserve_ratio
    function test_AllowsForcedRebalanceThresholdExactly10BPBelowReserveRatio() external view {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.forcedRebalanceThresholdBP = 189;

        bytes memory evmScript = registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    // python: test_infra_fee_too_high
    function test_RevertWhen_InfraFeeIsTooHigh() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.infraFeeBP = 70001;

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_liquidity_fee_too_high
    function test_RevertWhen_LiquidityFeeIsTooHigh() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.liquidityFeeBP = 70001;

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    // python: test_reservation_fee_too_high
    function test_RevertWhen_ReservationFeeIsTooHigh() external {
        TierParams memory tier = Vaults.defaultTierParams();
        tier.reservationFeeBP = 70001;

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        registerGroupsInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_OPERATOR, GROUP_SHARE_LIMIT, tier)
        );
    }

    /// @dev python: operatorGrid.registerGroup(nodeOperator, shareLimit, {"from": owner})
    function _registerGroup(address nodeOperator, uint256 shareLimit) private {
        vm.prank(owner);
        operatorGrid.registerGroup(nodeOperator, shareLimit);
    }

    function _operators(address nodeOperator)
        private
        pure
        returns (address[] memory nodeOperators)
    {
        nodeOperators = new address[](1);
        nodeOperators[0] = nodeOperator;
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

    function _shareLimits(uint256 shareLimit) private pure returns (uint256[] memory shareLimits) {
        shareLimits = new uint256[](1);
        shareLimits[0] = shareLimit;
    }

    function _shareLimits(uint256 first, uint256 second)
        private
        pure
        returns (uint256[] memory shareLimits)
    {
        shareLimits = new uint256[](2);
        shareLimits[0] = first;
        shareLimits[1] = second;
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

    /// @dev python: create_calldata([nodeOperator], [shareLimit], [[tier]])
    function _encodeCallData(address nodeOperator, uint256 shareLimit, TierParams memory tier)
        private
        pure
        returns (bytes memory)
    {
        return
            abi.encode(
                _operators(nodeOperator), _shareLimits(shareLimit), _tiers(_tierParams(tier))
            );
    }

    /// @dev python: create_calldata([first, second], [1000, 2000], [[DEFAULT], [DEFAULT]]), the
    /// shape of the ordering tests
    function _encodePairCallData(address first, address second)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(
            _operators(first, second),
            _shareLimits(1000, 2000),
            _tiers(_tierParams(Vaults.defaultTierParams()), _tierParams(Vaults.defaultTierParams()))
        );
    }

    /// @dev python: encode_call_script of registerGroup then registerTiers per operator, every call
    /// to the operator grid
    function _registerGroupsScript(
        address[] memory nodeOperators,
        uint256[] memory shareLimits,
        TierParams[][] memory tiers
    ) private view returns (bytes memory) {
        bytes[] memory calls = new bytes[](nodeOperators.length * 2);

        for (uint256 i; i < nodeOperators.length; ++i) {
            calls[i * 2] = abi.encodeWithSelector(
                IOperatorGrid.registerGroup.selector, nodeOperators[i], shareLimits[i]
            );
            calls[i * 2 + 1] = abi.encodeWithSelector(
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
