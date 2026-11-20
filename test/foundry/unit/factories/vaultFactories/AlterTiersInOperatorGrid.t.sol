// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    AlterTiersInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/AlterTiersInOperatorGrid.sol";
import {IOperatorGrid, TierParams} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract AlterTiersInOperatorGridTest is Test {
    uint256 internal constant DEFAULT_TIER_MAX_SHARE_LIMIT = 1000 * 1e18;
    uint256 internal constant DEFAULT_TIER_ID = 0;
    /// @dev The id of the first tier registered after the default one
    uint256 internal constant FIRST_TIER_ID = 1;
    uint256 internal constant MISSING_TIER_ID = 99;
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

    function test_SetsInitialState() external view {
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

    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        alterTiersInOperatorGrid.createEVMScript(stranger, "");
    }

    function test_RevertWhen_TierIdsAreEmpty() external {
        uint256[] memory tierIds = new uint256[](0);
        TierParams[] memory tierParams = new TierParams[](0);

        vm.expectRevert("EMPTY_TIER_IDS");
        alterTiersInOperatorGrid.createEVMScript(owner, abi.encode(tierIds, tierParams));
    }

    function test_RevertWhen_ArrayLengthsMismatch() external {
        uint256[] memory tierIds = Arrays.list(DEFAULT_TIER_ID, FIRST_TIER_ID);
        TierParams[] memory tierParams = Arrays.list(Vaults.defaultTierParams());

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        alterTiersInOperatorGrid.createEVMScript(owner, abi.encode(tierIds, tierParams));
    }

    function test_RevertWhen_TierDoesNotExist() external {
        vm.expectRevert("TIER_NOT_EXISTS");
        alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(MISSING_TIER_ID, Vaults.defaultTierParams())
        );
    }

    function test_RevertWhen_CallDataLengthIsWrong() external {
        vm.expectRevert(bytes(""));
        alterTiersInOperatorGrid.createEVMScript(owner, hex"00");
    }

    function test_CreatesEVMScript() external {
        _registerGroupWithTiers(
            9000, Arrays.list(Vaults.defaultTierParams(), Vaults.defaultTierParams())
        );

        uint256[] memory tierIds = Arrays.list(FIRST_TIER_ID, FIRST_TIER_ID + 1);
        TierParams[] memory tierParams = Arrays.list(
            Vaults.tierParams(2000, 300, 150, 75, 60, 20),
            Vaults.tierParams(3000, 400, 200, 100, 80, 30)
        );

        bytes memory evmScript =
            alterTiersInOperatorGrid.createEVMScript(owner, abi.encode(tierIds, tierParams));

        assertEq(evmScript, _alterTiersScript(tierIds, tierParams), "evmScript");
    }

    function test_DecodesEVMScriptCallData() external view {
        uint256[] memory tierIds = Arrays.list(FIRST_TIER_ID, FIRST_TIER_ID + 1);
        TierParams[] memory tierParams =
            Arrays.list(Vaults.defaultTierParams(), Vaults.tierParams(2000, 300, 150, 75, 60, 20));

        (uint256[] memory decodedTierIds, TierParams[] memory decodedTierParams) =
            alterTiersInOperatorGrid.decodeEVMScriptCallData(abi.encode(tierIds, tierParams));

        assertEq(decodedTierIds, tierIds, "tierIds");
        Vaults.assertTierParamsEq(decodedTierParams, tierParams);
    }

    function test_RevertWhen_ReserveRatioIsZero() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.reserveRatioBP = 0;

        vm.expectRevert("ZERO_RESERVE_RATIO");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_ReserveRatioIsTooHigh() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.reserveRatioBP = 70001;

        vm.expectRevert("RESERVE_RATIO_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_ForcedRebalanceThresholdIsZero() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 0;

        vm.expectRevert("ZERO_FORCED_REBALANCE_THRESHOLD");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_ForcedRebalanceThresholdIsTooHigh() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 300;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_ForcedRebalanceThresholdEqualsReserveRatio() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = tierParams.reserveRatioBP;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_ForcedRebalanceThresholdIsWithin10BPOfReserveRatio() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 191;

        vm.expectRevert("FORCED_REBALANCE_THRESHOLD_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_AllowsForcedRebalanceThresholdExactly10BPBelowReserveRatio() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.forcedRebalanceThresholdBP = 189;

        bytes memory evmScript = alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_TIER_ID, tierParams)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    function test_RevertWhen_InfraFeeIsTooHigh() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.infraFeeBP = 70001;

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_LiquidityFeeIsTooHigh() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.liquidityFeeBP = 70001;

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_ReservationFeeIsTooHigh() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.reservationFeeBP = 70001;

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_AnyFeeExceedsUint16Max() external {
        _registerGroupWithDefaultTier();

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

    function test_AllowsTierShareLimitAboveGroupShareLimit() external {
        _registerGroupWithDefaultTier();

        // the group share limit is enforced by the operator grid at minting time, not here
        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = 2000;

        bytes memory evmScript = alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(FIRST_TIER_ID, tierParams)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    function test_RevertWhen_TierShareLimitIsTooHigh() external {
        _registerGroupWithDefaultTier();

        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = Vaults.MAX_TIER_SHARE_LIMIT + 1;

        vm.expectRevert("TIER_SHARE_LIMIT_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(owner, _encodeCallData(FIRST_TIER_ID, tierParams));
    }

    function test_RevertWhen_DefaultTierShareLimitExceedsMaxLimit() external {
        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = DEFAULT_TIER_MAX_SHARE_LIMIT + 1;

        vm.expectRevert("TIER_SHARE_LIMIT_TOO_HIGH");
        alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(DEFAULT_TIER_ID, tierParams)
        );
    }

    function test_AllowsDefaultTierShareLimitAtMaxLimit() external view {
        TierParams memory tierParams = Vaults.defaultTierParams();
        tierParams.shareLimit = DEFAULT_TIER_MAX_SHARE_LIMIT;

        bytes memory evmScript = alterTiersInOperatorGrid.createEVMScript(
            owner, _encodeCallData(DEFAULT_TIER_ID, tierParams)
        );

        assertGt(evmScript.length, 0, "evmScript.length");
    }

    function _registerGroupWithTiers(uint256 shareLimit, TierParams[] memory tiers) private {
        vm.startPrank(owner);
        operatorGrid.registerGroup(OPERATOR, shareLimit);
        operatorGrid.registerTiers(OPERATOR, tiers);
        vm.stopPrank();
    }

    /// @dev The arrangement the bound tests share: a group of share limit 1000 with one default
    /// tier, registered as `FIRST_TIER_ID`
    function _registerGroupWithDefaultTier() private {
        _registerGroupWithTiers(GROUP_SHARE_LIMIT, Arrays.list(Vaults.defaultTierParams()));
    }

    function _encodeCallData(uint256 tierId, TierParams memory params)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(Arrays.list(tierId), Arrays.list(params));
    }

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
}
