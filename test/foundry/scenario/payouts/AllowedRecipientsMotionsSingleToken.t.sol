// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {IntegrationTestAddresses} from "test/foundry/helpers/IntegrationTestAddresses.sol";
import {SingleTokenPayoutsScenarioBase} from "test/foundry/helpers/PayoutsScenarioBase.sol";
import {IAllowedRecipientsRegistry} from "test/foundry/interfaces/Payouts.sol";

/// @notice The single-token allowed recipients motions over a registry and its three factories,
///         recipient add and remove, top-ups within the period limit, the period rollover and the
///         limit changes a motion can meet in flight. The Brownie suite runs the file once per
///         `single_token` instance of `integration-test-addresses-<chain>.yaml`, so does each
///         contract below: the listed registry and factories, a missing factory deployed fresh
///         over the listed registry, or, on a chain without the file, everything fresh paying LDO.
abstract contract AllowedRecipientsMotionsSingleTokenTest is SingleTokenPayoutsScenarioBase {
    string internal constant SUM_EXCEEDS_SPENDABLE_BALANCE = "SUM_EXCEEDS_SPENDABLE_BALANCE";

    function _instanceName() internal pure virtual returns (string memory);

    function setUp() public override {
        super.setUp();

        _bindInstance(_instanceName());
    }

    function testFork_AddsRecipientByMotion() external {
        uint256 countBefore = allowedRecipientsRegistry.getAllowedRecipients().length;
        bytes memory callData = abi.encode(recipients[0], titles[0]);
        uint256 motionId =
            _createMotion(addAllowedRecipient, _trustedCaller(addAllowedRecipient), callData);

        _passMotionDuration();

        vm.expectEmit(address(allowedRecipientsRegistry));
        emit IAllowedRecipientsRegistry.RecipientAdded(recipients[0], titles[0]);

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipients[0]), "recipient allowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients().length, countBefore + 1, "recipients"
        );
    }

    function testFork_AddsMultipleRecipientsByConcurrentMotions() external {
        uint256 countBefore = allowedRecipientsRegistry.getAllowedRecipients().length;
        bytes memory firstCallData = abi.encode(recipients[0], titles[0]);
        bytes memory secondCallData = abi.encode(recipients[1], titles[1]);
        uint256 firstMotionId =
            _createMotion(addAllowedRecipient, _trustedCaller(addAllowedRecipient), firstCallData);
        uint256 secondMotionId =
            _createMotion(addAllowedRecipient, _trustedCaller(addAllowedRecipient), secondCallData);

        _enactMotion(firstMotionId, firstCallData);
        _enactMotion(secondMotionId, secondCallData);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipients[0]), "first allowed");
        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "second allowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients().length, countBefore + 2, "recipients"
        );
    }

    function testFork_RevertWhen_SameRecipientAddedBySecondConcurrentMotion() external {
        bytes memory callData = abi.encode(recipients[0], titles[0]);
        uint256 firstMotionId =
            _createMotion(addAllowedRecipient, _trustedCaller(addAllowedRecipient), callData);
        uint256 secondMotionId =
            _createMotion(addAllowedRecipient, _trustedCaller(addAllowedRecipient), callData);

        _enactMotion(firstMotionId, callData);

        vm.prank(stranger);
        vm.expectRevert("ALLOWED_RECIPIENT_ALREADY_ADDED");
        easyTrack.enactMotion(secondMotionId, callData);
    }

    function testFork_RevertWhen_SameRecipientAddedTwice() external {
        _addRecipientByMotion(recipients[0], titles[0]);

        vm.prank(_trustedCaller(addAllowedRecipient));
        vm.expectRevert("ALLOWED_RECIPIENT_ALREADY_ADDED");
        easyTrack.createMotion(addAllowedRecipient, abi.encode(recipients[0], titles[0]));
    }

    function testFork_RemovesRecipientByMotion() external {
        uint256 countBefore = allowedRecipientsRegistry.getAllowedRecipients().length;
        _addRecipientByMotion(recipients[0], titles[0]);

        bytes memory callData = abi.encode(recipients[0]);
        uint256 motionId =
            _createMotion(removeAllowedRecipient, _trustedCaller(removeAllowedRecipient), callData);

        _passMotionDuration();

        vm.expectEmit(address(allowedRecipientsRegistry));
        emit IAllowedRecipientsRegistry.RecipientRemoved(recipients[0]);

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertFalse(
            allowedRecipientsRegistry.isRecipientAllowed(recipients[0]), "recipient removed"
        );
        assertEq(allowedRecipientsRegistry.getAllowedRecipients().length, countBefore, "recipients");
    }

    function testFork_RevertWhen_RemovingFromEmptyAllowedRecipientsList() external {
        address[] memory allowed = allowedRecipientsRegistry.getAllowedRecipients();
        for (uint256 index; index < allowed.length; ++index) {
            _removeRecipientByMotion(allowed[index]);
        }

        assertEq(allowedRecipientsRegistry.getAllowedRecipients().length, 0, "recipients");

        vm.prank(_trustedCaller(removeAllowedRecipient));
        vm.expectRevert("ALLOWED_RECIPIENT_NOT_FOUND");
        easyTrack.createMotion(removeAllowedRecipient, abi.encode(recipients[0]));
    }

    function testFork_RevertWhen_RemovingNotAllowedRecipient() external {
        _addRecipientByMotion(recipients[0], titles[0]);

        assertGt(allowedRecipientsRegistry.getAllowedRecipients().length, 0, "recipients");
        assertFalse(allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "not allowed");

        vm.prank(_trustedCaller(removeAllowedRecipient));
        vm.expectRevert("ALLOWED_RECIPIENT_NOT_FOUND");
        easyTrack.createMotion(removeAllowedRecipient, abi.encode(recipients[1]));
    }

    function testFork_TopsUpSingleRecipient() external {
        (, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _addRecipientByMotion(recipients[0], titles[0]);

        _advanceToNextPeriod(periodDuration);

        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(2e18)), SPENT_AMOUNT
        );
    }

    function testFork_TopsUpSingleRecipientSeveralTimesInPeriod() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _ensureAgentTokenBalance(2 * limit);
        _addRecipientByMotion(recipients[0], titles[0]);

        _advanceToNextPeriod(periodDuration);

        bytes memory halfLimit = _encodeTopUp(_recipients(1), _amounts(limit / 2));
        _topUpByMotion(topUpAllowedRecipients, halfLimit, SPENT_AMOUNT);
        _topUpByMotion(topUpAllowedRecipients, halfLimit, limit / 2);

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(1)));

        _advanceToNextPeriod(periodDuration);

        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(limit)), SPENT_AMOUNT
        );
    }

    function testFork_TopsUpMultipleRecipients() external {
        (, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);

        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(2), _amounts(2e18, 1e18)), SPENT_AMOUNT
        );
    }

    function testFork_EnactsTopUpMotionInNextPeriod() external {
        (, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);

        bytes memory callData = _encodeTopUp(_recipients(2), _amounts(3e18, 90e18));
        uint256 motionId = _createTopUpMotion(topUpAllowedRecipients, callData);

        vm.warp(vm.getBlockTimestamp() + periodDuration * MAX_SECONDS_IN_MONTH);

        _enactTopUpMotion(motionId, callData, SPENT_AMOUNT);
    }

    function testFork_EnactsEndedTopUpMotionInNextPeriod() external {
        (, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);
        _advanceToBeforePeriodEnd(periodDuration, easyTrack.motionDuration() / 2);

        bytes memory callData = _encodeTopUp(_recipients(2), _amounts(3e18, 90e18));
        uint256 motionId = _createTopUpMotion(topUpAllowedRecipients, callData);
        (,, uint256 oldPeriodStart, uint256 oldPeriodEnd) =
            allowedRecipientsRegistry.getPeriodState();

        _enactTopUpMotion(motionId, callData, SPENT_AMOUNT);

        (,, uint256 newPeriodStart, uint256 newPeriodEnd) =
            allowedRecipientsRegistry.getPeriodState();
        assertNotEq(newPeriodStart, oldPeriodStart, "period start");
        assertNotEq(newPeriodEnd, oldPeriodEnd, "period end");
    }

    function testFork_EnactsTopUpMotionInSecondNextPeriod() external {
        (, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);

        bytes memory callData = _encodeTopUp(_recipients(2), _amounts(3e18, 90e18));
        uint256 motionId = _createTopUpMotion(topUpAllowedRecipients, callData);

        vm.warp(vm.getBlockTimestamp() + 2 * periodDuration * MAX_SECONDS_IN_MONTH);

        _enactTopUpMotion(motionId, callData, SPENT_AMOUNT);
    }

    function testFork_RenewsSpendableBalanceInNextPeriod() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _ensureAgentTokenBalance(2 * limit);

        _advanceToNextPeriod(periodDuration);

        assertEq(allowedRecipientsRegistry.spendableBalance(), limit, "spendable before payouts");

        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        uint256[] memory amounts = _amounts(limit / 10, limit / 10 * 9);
        _topUpByMotion(topUpAllowedRecipients, _encodeTopUp(_recipients(2), amounts), SPENT_AMOUNT);

        (uint256 alreadySpentAmount,,,) = allowedRecipientsRegistry.getPeriodState();
        assertEq(alreadySpentAmount, _sum(amounts), "_alreadySpentAmount");
        assertEq(allowedRecipientsRegistry.spendableBalance(), limit - _sum(amounts), "spendable");

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(1)));

        // The views are not refreshed by the rollover, so renewal shows as a full-limit payout
        vm.warp(vm.getBlockTimestamp() + periodDuration * MAX_SECONDS_IN_MONTH);

        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(limit)), SPENT_AMOUNT
        );

        (alreadySpentAmount,,,) = allowedRecipientsRegistry.getPeriodState();
        assertEq(alreadySpentAmount, limit, "_alreadySpentAmount after renewal");
        assertEq(allowedRecipientsRegistry.spendableBalance(), 0, "spendable after renewal");
    }

    function testFork_RevertWhen_RecipientRemovedByOtherMotion() external {
        (, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();

        _advanceToNextPeriod(periodDuration);

        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        bytes memory callData = _encodeTopUp(_recipients(2), _amounts(40e18, 30e18));
        uint256 motionId = _createTopUpMotion(topUpAllowedRecipients, callData);
        _removeRecipientByMotion(recipients[0]);

        vm.prank(stranger);
        vm.expectRevert("RECIPIENT_NOT_ALLOWED");
        easyTrack.enactMotion(motionId, callData);
    }

    function testFork_RevertWhen_TopUpMotionExceedsLimit() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _addRecipientByMotion(recipients[0], titles[0]);

        _advanceToNextPeriod(periodDuration);

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(limit + 1))
        );
    }

    function testFork_RevertWhen_TopUpMotionExceedsSpendable() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _ensureAgentTokenBalance(limit);
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);

        uint256[] memory amounts = _amounts(limit / 10 * 4, limit / 10 * 6);
        assertEq(_sum(amounts), limit, "setup: amounts sum to the limit");

        _topUpByMotion(topUpAllowedRecipients, _encodeTopUp(_recipients(2), amounts), SPENT_AMOUNT);

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(topUpAllowedRecipients, _encodeTopUp(_recipients(2), _amounts(1, 1)));
    }

    function testFork_EnactsSecondTopUpMotionInNextPeriodAfterLimitRejection() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _ensureAgentTokenBalance(2 * limit);
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);

        uint256[] memory firstAmounts = _amounts(limit / 10 * 4, limit / 10 * 3);
        uint256[] memory secondAmounts = _amounts(limit / 10 * 3, limit / 10 * 2);
        assertGt(_sum(firstAmounts) + _sum(secondAmounts), limit, "setup: amounts exceed limit");

        bytes memory firstCallData = _encodeTopUp(_recipients(2), firstAmounts);
        bytes memory secondCallData = _encodeTopUp(_recipients(2), secondAmounts);
        uint256 firstMotionId = _createTopUpMotion(topUpAllowedRecipients, firstCallData);
        uint256 secondMotionId = _createTopUpMotion(topUpAllowedRecipients, secondCallData);

        _enactTopUpMotion(firstMotionId, firstCallData, SPENT_AMOUNT);

        vm.prank(stranger);
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.enactMotion(secondMotionId, secondCallData);

        vm.warp(vm.getBlockTimestamp() + periodDuration * MAX_SECONDS_IN_MONTH);

        _enactTopUpMotion(secondMotionId, secondCallData, SPENT_AMOUNT);
    }

    function testFork_RevertWhen_SecondTopUpMotionCreationExceedsSpendable() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _ensureAgentTokenBalance(limit);
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);

        uint256[] memory firstAmounts = _amounts(limit / 100 * 3, limit / 10 * 9);
        uint256[] memory secondAmounts = _amounts(limit / 100 * 5, limit / 100 * 4);
        assertGt(_sum(firstAmounts) + _sum(secondAmounts), limit, "setup: amounts exceed limit");

        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(2), firstAmounts), SPENT_AMOUNT
        );

        assertGt(
            _sum(secondAmounts), allowedRecipientsRegistry.spendableBalance(), "second exceeds"
        );

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(topUpAllowedRecipients, _encodeTopUp(_recipients(2), secondAmounts));
    }

    function testFork_RevertWhen_LimitDecreasedWhileMotionIsInFlight() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _addRecipientByMotion(recipients[0], titles[0]);

        _advanceToNextPeriod(periodDuration);

        bytes memory callData = _encodeTopUp(_recipients(1), _amounts(limit));
        uint256 motionId = _createTopUpMotion(topUpAllowedRecipients, callData);

        vm.prank(agent);
        allowedRecipientsRegistry.setLimitParameters(limit / 2, periodDuration);

        _passMotionDuration();

        vm.prank(stranger);
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.enactMotion(motionId, callData);
    }

    function testFork_TopsUpWhenLimitIncreasesWhileMotionIsInFlight() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _ensureAgentTokenBalance(limit);
        _addRecipientByMotion(recipients[0], titles[0]);

        _advanceToNextPeriod(periodDuration);

        bytes memory callData = _encodeTopUp(_recipients(1), _amounts(limit));
        uint256 motionId = _createTopUpMotion(topUpAllowedRecipients, callData);

        vm.prank(agent);
        allowedRecipientsRegistry.setLimitParameters(3 * limit, periodDuration);

        _enactTopUpMotion(motionId, callData, SPENT_AMOUNT);
    }

    function testFork_EnactsSecondMotionAfterLimitIncrease() external {
        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        _ensureAgentTokenBalance(2 * limit);
        _addRecipientByMotion(recipients[0], titles[0]);
        _addRecipientByMotion(recipients[1], titles[1]);

        _advanceToNextPeriod(periodDuration);

        uint256[] memory firstAmounts = _amounts(limit / 10 * 4, limit / 10 * 6);
        uint256[] memory secondAmounts = _amounts(1, 1);
        assertEq(_sum(firstAmounts), limit, "setup: amounts sum to the limit");

        bytes memory firstCallData = _encodeTopUp(_recipients(2), firstAmounts);
        bytes memory secondCallData = _encodeTopUp(_recipients(2), secondAmounts);
        uint256 firstMotionId = _createTopUpMotion(topUpAllowedRecipients, firstCallData);
        uint256 secondMotionId = _createTopUpMotion(topUpAllowedRecipients, secondCallData);

        _enactTopUpMotion(firstMotionId, firstCallData, SPENT_AMOUNT);

        vm.prank(stranger);
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.enactMotion(secondMotionId, secondCallData);

        vm.prank(agent);
        allowedRecipientsRegistry.setLimitParameters(limit + _sum(secondAmounts), periodDuration);

        _passMotionDuration();

        // The first payout sits in the same period, so the enactment check does not apply
        vm.prank(stranger);
        easyTrack.enactMotion(secondMotionId, secondCallData);
    }

    function testFork_RenewsSpendableWhenPeriodDurationChanges_3To2() external {
        _spendableRenewalIfPeriodDurationChanged(3, 2);
    }

    function testFork_RenewsSpendableWhenPeriodDurationChanges_3To6() external {
        _spendableRenewalIfPeriodDurationChanged(3, 6);
    }

    function testFork_RenewsSpendableWhenPeriodDurationChanges_12To1() external {
        _spendableRenewalIfPeriodDurationChanged(12, 1);
    }

    function testFork_RenewsSpendableWhenPeriodDurationChanges_1To12() external {
        _spendableRenewalIfPeriodDurationChanged(1, 12);
    }

    function testFork_SetsLimitParametersByAragonAgentViaVoting() external {
        // The vote forwards the call through the Agent, replayed as the Agent's call
        vm.prank(agent);
        allowedRecipientsRegistry.setLimitParameters(100e18, 6);

        (uint256 limit, uint256 periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        assertEq(limit, 100e18, "limit");
        assertEq(periodDuration, 6, "periodDurationMonths");
    }

    /// @dev Changing the period duration reshapes the calendar grid but keeps the spent amount, so
    ///      the spendable balance renews only in the next period of the new grid
    function _spendableRenewalIfPeriodDurationChanged(
        uint256 initialPeriodDuration,
        uint256 newPeriodDuration
    ) private {
        uint256 periodLimit = 100e18;
        _addRecipientByMotion(recipients[0], titles[0]);

        vm.prank(agent);
        allowedRecipientsRegistry.setLimitParameters(periodLimit, initialPeriodDuration);

        _advanceToMiddleOfNextPeriod(initialPeriodDuration);

        _topUpByMotion(
            topUpAllowedRecipients,
            _encodeTopUp(_recipients(1), _amounts(periodLimit)),
            SPENT_AMOUNT
        );

        bytes memory oneWei = _encodeTopUp(_recipients(1), _amounts(1));

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(topUpAllowedRecipients, oneWei);

        vm.prank(agent);
        allowedRecipientsRegistry.setLimitParameters(periodLimit, newPeriodDuration);

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(topUpAllowedRecipients, oneWei);

        _advanceToMiddleOfNextPeriod(newPeriodDuration);

        _topUpByMotion(topUpAllowedRecipients, oneWei, SPENT_AMOUNT);
    }
}

// --- one contract per `single_token` instance, the pytest ids of `deployed_contracts` ---

contract AllowedRecipientsMotionsSingleTokenLOLStETHTest is
    AllowedRecipientsMotionsSingleTokenTest
{
    function _instanceName() internal pure override returns (string memory) {
        return "LOL stETH";
    }
}

contract AllowedRecipientsMotionsSingleTokenRewardsShareStETHTest is
    AllowedRecipientsMotionsSingleTokenTest
{
    function _instanceName() internal pure override returns (string memory) {
        return "Rewards Share stETH";
    }
}

contract AllowedRecipientsMotionsSingleTokenLEGOLDOTest is AllowedRecipientsMotionsSingleTokenTest {
    function _instanceName() internal pure override returns (string memory) {
        return "LEGO LDO";
    }
}

contract AllowedRecipientsMotionsSingleTokenTRPLDOTest is AllowedRecipientsMotionsSingleTokenTest {
    function _instanceName() internal pure override returns (string memory) {
        return "TRP LDO";
    }
}

contract AllowedRecipientsMotionsSingleTokenGasSupplyStETHTest is
    AllowedRecipientsMotionsSingleTokenTest
{
    function _instanceName() internal pure override returns (string memory) {
        return "Gas Supply stETH";
    }
}

contract AllowedRecipientsMotionsSingleTokenStonksStETHTest is
    AllowedRecipientsMotionsSingleTokenTest
{
    function _instanceName() internal pure override returns (string memory) {
        return "Stonks stETH";
    }
}

/// @notice The chain without an addresses file: everything deployed fresh, paying LDO
contract AllowedRecipientsMotionsSingleTokenDefaultTest is AllowedRecipientsMotionsSingleTokenTest {
    function _instanceName() internal pure override returns (string memory) {
        return IntegrationTestAddresses.DEFAULT_INSTANCE;
    }
}
