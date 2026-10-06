// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    AlterTiersInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/AlterTiersInOperatorGrid.sol";
import {IOperatorGrid, TierParams} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract AlterTiersInOperatorGridTest is Test {
    /// @dev python: max_share_limit of the fixture, the defaultTierMaxShareLimit constructor argument
    uint256 internal constant DEFAULT_TIER_MAX_SHARE_LIMIT = 1000 * 1e18;
    uint256 internal constant DEFAULT_TIER_ID = 0;
    /// @dev The id of the first tier registered after the default one
    uint256 internal constant FIRST_TIER_ID = 1;
    uint256 internal constant MISSING_TIER_ID = 99;
    /// @dev python: operator_address
    address internal constant OPERATOR = address(1);
    uint256 internal constant GROUP_SHARE_LIMIT = 1000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    LidoLocatorStub internal lidoLocatorStub;
    IOperatorGrid internal operatorGrid;
    AlterTiersInOperatorGrid internal alterTiersInOperatorGrid;

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        operatorGrid = IOperatorGrid(lidoLocatorStub.operatorGrid());

        vm.prank(owner);
        alterTiersInOperatorGrid = new AlterTiersInOperatorGrid(
            owner, address(lidoLocatorStub), DEFAULT_TIER_MAX_SHARE_LIMIT
        );

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(operatorGrid), "operatorGridStub");
        vm.label(address(alterTiersInOperatorGrid), "alterTiersInOperatorGrid");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(alterTiersInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(alterTiersInOperatorGrid.lidoLocator()), address(lidoLocatorStub), "lidoLocator"
        );
        assertEq(
            alterTiersInOperatorGrid.defaultTierMaxShareLimit(),
            DEFAULT_TIER_MAX_SHARE_LIMIT,
            "defaultTierMaxShareLimit"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        alterTiersInOperatorGrid.createEVMScript(stranger, "");
    }

    // python: test_empty_tier_ids_array
    function test_RevertWhen_TierIdsAreEmpty() external {
        uint256[] memory tierIds = new uint256[](0);
        TierParams[] memory tierParams = new TierParams[](0);

        vm.expectRevert("EMPTY_TIER_IDS");
        alterTiersInOperatorGrid.createEVMScript(owner, abi.encode(tierIds, tierParams));
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        uint256[] memory tierIds = _tierIds(DEFAULT_TIER_ID, FIRST_TIER_ID);
        TierParams[] memory tierParams = _tierParams(Vaults.defaultTierParams());

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        alterTiersInOperatorGrid.createEVMScript(owner, abi.encode(tierIds, tierParams));
    }

    // python: test_tier_not_exists
    function test_RevertWhen_TierDoesNotExist() external {
        vm.expectRevert("TIER_NOT_EXISTS");
        alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(MISSING_TIER_ID, Vaults.defaultTierParams())
        );
    }

    // python: test_wrong_calldata_length
    function test_RevertWhen_CallDataLengthIsWrong() external {
        vm.expectRevert(bytes(""));
        alterTiersInOperatorGrid.createEVMScript(owner, hex"00");
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        _givenGroupWithTiers(
            9000, _tierParams(Vaults.defaultTierParams(), Vaults.defaultTierParams())
        );

        uint256[] memory tierIds = _tierIds(FIRST_TIER_ID, FIRST_TIER_ID + 1);
        TierParams[] memory tierParams = _tierParams(
            Vaults.tierParams(2000, 300, 150, 75, 60, 20),
            Vaults.tierParams(3000, 400, 200, 100, 80, 30)
        );

        bytes memory evmScript =
            alterTiersInOperatorGrid.createEVMScript(owner, abi.encode(tierIds, tierParams));

        assertEq(evmScript, _alterTiersScript(tierIds, tierParams), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        uint256[] memory tierIds = _tierIds(FIRST_TIER_ID, FIRST_TIER_ID + 1);
        TierParams[] memory tierParams =
            _tierParams(Vaults.defaultTierParams(), Vaults.tierParams(2000, 300, 150, 75, 60, 20));

        (uint256[] memory decodedTierIds, TierParams[] memory decodedTierParams) =
            alterTiersInOperatorGrid.decodeEVMScriptCallData(abi.encode(tierIds, tierParams));

        assertEq(decodedTierIds, tierIds, "tierIds");
        _assertTierParamsEq(decodedTierParams, tierParams);
    }

    // python: test_zero_reserve_ratio
    function test_RevertWhen_ReserveRatioIsZero() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.reserveRatioBP = 0;

        vm.expectRevert("ZERO_RESERVE_RATIO");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_reserve_ratio_too_high
    function test_RevertWhen_ReserveRatioIsTooHigh() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.reserveRatioBP = 70001;

        vm.expectRevert("RESERVE_RATIO_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_zero_forced_rebalance_threshold
    function test_RevertWhen_ForcedRebalanceThresholdIsZero() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 0;

        vm.expectRevert("ZERO_FORCED_REBALANCE_THRESHOLD");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_forced_rebalance_threshold_too_high
    function test_RevertWhen_ForcedRebalanceThresholdIsTooHigh() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 300;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_forced_rebalance_threshold_equals_reserve_ratio
    function test_RevertWhen_ForcedRebalanceThresholdEqualsReserveRatio() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = tierParams.reserveRatioBP;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_forced_rebalance_threshold_within_10bp_of_reserve_ratio
    function test_RevertWhen_ForcedRebalanceThresholdIsWithin10BPOfReserveRatio() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 191;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_forced_rebalance_threshold_exactly_10bp_below_reserve_ratio
    function test_AllowsForcedRebalanceThresholdExactly10BPBelowReserveRatio() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 189;

        bytes memory evmScript = alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_TIER_ID, tierParams)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    // python: test_infra_fee_too_high
    function test_RevertWhen_InfraFeeIsTooHigh() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.infraFeeBP = 70001;

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_liquidity_fee_too_high
    function test_RevertWhen_LiquidityFeeIsTooHigh() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.liquidityFeeBP = 70001;

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_reservation_fee_too_high
    function test_RevertWhen_ReservationFeeIsTooHigh() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.reservationFeeBP = 70001;

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_fees_less_than_uint16_max
    function test_RevertWhen_AnyFeeExceedsUint16Max() external {
        _givenGroupWithDefaultTier();

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(
            owner,
            _encodeCallData(FIRST_TIER_ID, Vaults.tierParams(1000, 200, 100, 70001, 100, 100))
        );

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(
            owner,
            _encodeCallData(FIRST_TIER_ID, Vaults.tierParams(1000, 200, 100, 100, 70001, 100))
        );

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(
            owner,
            _encodeCallData(FIRST_TIER_ID, Vaults.tierParams(1000, 200, 100, 100, 100, 70001))
        );
    }

    // python: test_share_limit_exceeds_group_share_limit
    function test_AllowsTierShareLimitAboveGroupShareLimit() external {
        _givenGroupWithDefaultTier();

        // the group share limit is enforced by the operator grid at minting time, not here
        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = 2000;

        bytes memory evmScript = alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_TIER_ID, tierParams)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    // python: test_tier_share_limit_too_high
    function test_RevertWhen_TierShareLimitIsTooHigh() external {
        _givenGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = Vaults.MAX_TIER_SHARE_LIMIT + 1;

        vm.expectRevert("TIER_SHARE_LIMIT_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    // python: test_default_tier_share_limit_exceeds_max_limit
    function test_RevertWhen_DefaultTierShareLimitExceedsMaxLimit() external {
        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = DEFAULT_TIER_MAX_SHARE_LIMIT + 1;

        vm.expectRevert("TIER_SHARE_LIMIT_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(DEFAULT_TIER_ID, tierParams)
        );
    }

    // python: test_default_tier_share_limit_at_max_limit
    function test_AllowsDefaultTierShareLimitAtMaxLimit() external view {
        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = DEFAULT_TIER_MAX_SHARE_LIMIT;

        bytes memory evmScript = alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(DEFAULT_TIER_ID, tierParams)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    /// @dev python: operator_grid_stub.registerGroup(operator_address, shareLimit, {"from": owner})
    /// then registerTiers(operator_address, tiers, {"from": owner})
    function _givenGroupWithTiers(uint256 shareLimit, TierParams[] memory tiers) private {
        vm.startPrank(owner);
        operatorGrid.registerGroup(OPERATOR, shareLimit);
        operatorGrid.registerTiers(OPERATOR, tiers);
        vm.stopPrank();
    }

    /// @dev The arrangement the bound tests share: a group of share limit 1000 with one default
    /// tier, registered as `FIRST_TIER_ID`
    function _givenGroupWithDefaultTier() private {
        _givenGroupWithTiers(GROUP_SHARE_LIMIT, _tierParams(Vaults.defaultTierParams()));
    }

    function _tierIds(uint256 first, uint256 second)
        private
        pure
        returns (uint256[] memory tierIds)
    {
        tierIds = new uint256[](2);
        tierIds[0] = first;
        tierIds[1] = second;
    }

    function _tierParams(TierParams memory params) private pure returns (TierParams[] memory list) {
        list = new TierParams[](1);
        list[0] = params;
    }

    function _tierParams(TierParams memory first, TierParams memory second)
        private
        pure
        returns (TierParams[] memory list)
    {
        list = new TierParams[](2);
        list[0] = first;
        list[1] = second;
    }

    /// @dev python: create_calldata([tierId], [params])
    function _encodeCallData(uint256 tierId, TierParams memory params)
        private
        pure
        returns (bytes memory)
    {
        uint256[] memory tierIds = new uint256[](1);
        tierIds[0] = tierId;

        return abi.encode(tierIds, _tierParams(params));
    }

    /// @dev python: encode_call_script([(operator_grid_stub, alterTiers.encode_input(tier_ids,
    /// tier_params))])
    function _alterTiersScript(uint256[] memory tierIds, TierParams[] memory tierParams)
        private
        view
        returns (bytes memory)
    {
        return EVMScripts.encodeCallScript(
            address(operatorGrid),
            abi.encodeWithSelector(IOperatorGrid.alterTiers.selector, tierIds, tierParams)
        );
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
