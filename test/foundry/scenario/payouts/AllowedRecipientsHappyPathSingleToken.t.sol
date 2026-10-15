// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {SingleTokenPayoutsScenarioBase} from "test/foundry/helpers/PayoutsScenarioBase.sol";
import {
    IAllowedRecipientsRegistry,
    ITopUpAllowedRecipientsSingleToken,
    ITrustedCaller
} from "test/foundry/interfaces/Payouts.sol";

/// @notice The two single-token setups `AllowedRecipientsBuilderSingleToken` deploys in one call,
///         paying LDO, driven end to end: a top-up-only registry of one recipient, and the full
///         setup with its add and remove factories. The Agent, not the executor, administers the
///         recipient list outside motions.
contract AllowedRecipientsHappyPathSingleTokenTest is SingleTokenPayoutsScenarioBase {
    string private constant SUM_EXCEEDS_SPENDABLE_BALANCE = "SUM_EXCEEDS_SPENDABLE_BALANCE";

    // python: test_single_recipient_top_up_only_setup_happy_path
    function testFork_SingleRecipientTopUpOnlySetupHappyPath() external {
        _advanceToNextPeriod(PERIOD_DURATION_MONTHS);

        _deploySingleRecipientTopUpOnlySetup();

        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(50e18)), SPENT_AMOUNT
        );

        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipients[0]), "recipient#1 allowed"
        );

        vm.prank(agent);
        allowedRecipientsRegistry.removeRecipient(recipients[0]);

        assertFalse(
            allowedRecipientsRegistry.isRecipientAllowed(recipients[0]), "recipient#1 removed"
        );

        _assertOnlyAgentManagesRecipients();

        vm.warp(vm.getBlockTimestamp() + MAX_SECONDS_IN_MONTH);

        _topUpByMotion(
            topUpAllowedRecipients,
            _encodeTopUp(_single(recipients[1]), _amounts(100e18)),
            SPENT_AMOUNT
        );

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(
            topUpAllowedRecipients, _encodeTopUp(_single(recipients[1]), _amounts(1))
        );
    }

    // python: test_full_setup_happy_path
    function testFork_FullSetupHappyPath() external {
        _advanceToNextPeriod(PERIOD_DURATION_MONTHS);

        _deployFullSetup();

        _addRecipientByMotion(recipients[0], titles[0]);
        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(_recipients(1), _amounts(50e18)), SPENT_AMOUNT
        );
        _removeRecipientByMotion(recipients[0]);

        assertFalse(
            allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "recipient#2 not allowed"
        );

        vm.prank(agent);
        allowedRecipientsRegistry.addRecipient(recipients[1], titles[1]);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "recipient#2 added");

        vm.warp(vm.getBlockTimestamp() + MAX_SECONDS_IN_MONTH);

        _topUpByMotion(
            topUpAllowedRecipients,
            _encodeTopUp(_single(recipients[1]), _amounts(100e18)),
            SPENT_AMOUNT
        );

        vm.prank(trustedCaller);
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(
            topUpAllowedRecipients, _encodeTopUp(_single(recipients[1]), _amounts(1))
        );

        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "recipient#2 allowed"
        );

        vm.prank(agent);
        allowedRecipientsRegistry.removeRecipient(recipients[1]);

        assertFalse(
            allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "recipient#2 removed"
        );
    }

    /// @dev python: single_recipient_top_up_only_setup. The recipient is the top-up factory's
    ///      trusted caller
    function _deploySingleRecipientTopUpOnlySetup() private {
        ITopUpAllowedRecipientsSingleToken topUp;
        (allowedRecipientsRegistry, topUp) = builder.deploySingleRecipientTopUpOnlySetup(
            recipients[0], titles[0], ldo, LIMIT, PERIOD_DURATION_MONTHS, SPENT_AMOUNT
        );
        topUpAllowedRecipients = address(topUp);

        vm.label(address(allowedRecipientsRegistry), "AllowedRecipientsRegistry");
        vm.label(topUpAllowedRecipients, "TopUpAllowedRecipientsSingleToken");

        _registerTopUpFactory(topUpAllowedRecipients);
    }

    /// @dev python: full_setup
    function _deployFullSetup() private {
        ITopUpAllowedRecipientsSingleToken topUp;
        ITrustedCaller add;
        ITrustedCaller remove;
        (allowedRecipientsRegistry, topUp, add, remove) = builder.deployFullSetup(
            trustedCaller,
            ldo,
            LIMIT,
            PERIOD_DURATION_MONTHS,
            new address[](0),
            new string[](0),
            SPENT_AMOUNT
        );
        topUpAllowedRecipients = address(topUp);
        addAllowedRecipient = address(add);
        removeAllowedRecipient = address(remove);

        vm.label(address(allowedRecipientsRegistry), "AllowedRecipientsRegistry");
        vm.label(topUpAllowedRecipients, "TopUpAllowedRecipientsSingleToken");
        vm.label(addAllowedRecipient, "AddAllowedRecipient");
        vm.label(removeAllowedRecipient, "RemoveAllowedRecipient");

        _registerAddFactory(addAllowedRecipient);
        _registerRemoveFactory(removeAllowedRecipient);
        _registerTopUpFactory(topUpAllowedRecipients);
    }

    /// @dev The top-up-only registry grants the executor no list roles: the Agent adds and
    ///      removes recipients, the executor is refused both
    function _assertOnlyAgentManagesRecipients() private {
        bytes memory addRefused = _accessRevertMessage(
            evmScriptExecutor, allowedRecipientsRegistry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE()
        );
        bytes memory removeRefused = _accessRevertMessage(
            evmScriptExecutor, allowedRecipientsRegistry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE()
        );

        vm.prank(evmScriptExecutor);
        vm.expectRevert(addRefused);
        allowedRecipientsRegistry.addRecipient(recipients[1], titles[1]);

        vm.prank(agent);
        allowedRecipientsRegistry.addRecipient(recipients[1], titles[1]);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "recipient#2 added");

        vm.prank(evmScriptExecutor);
        vm.expectRevert(removeRefused);
        allowedRecipientsRegistry.removeRecipient(recipients[1]);
    }
}
