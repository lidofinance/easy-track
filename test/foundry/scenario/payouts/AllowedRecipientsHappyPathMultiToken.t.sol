// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Vm} from "forge-std/Vm.sol";
import {MultiTokenPayoutsScenarioBase} from "test/foundry/helpers/PayoutsScenarioBase.sol";
import {
    IAllowedRecipientsFactory,
    IAllowedRecipientsRegistry,
    IAllowedTokensRegistry
} from "test/foundry/interfaces/Payouts.sol";

/// @notice The two multi-token setups `AllowedRecipientsBuilder` deploys in one call, driven end
///         to end: a top-up-only registry of one recipient, and the full setup with its add and
///         remove factories. The Agent, not the executor, administers the recipient and token
///         lists outside motions. The builder reports its deployments only through the factory
///         events, so each test reads them back from the logs.
contract AllowedRecipientsHappyPathMultiTokenTest is MultiTokenPayoutsScenarioBase {
    string private constant SUM_EXCEEDS_SPENDABLE_BALANCE = "SUM_EXCEEDS_SPENDABLE_BALANCE";

    // python: test_single_recipient_top_up_only_setup_happy_path
    function testFork_SingleRecipientTopUpOnlySetupHappyPath() external {
        _advanceToNextPeriod(PERIOD_DURATION_MONTHS);

        _deploySingleRecipientTopUpOnlySetup();

        _topUpByMotion(
            topUpAllowedRecipients,
            _encodeTopUp(dai, _recipients(1), _amounts(100e18)),
            SPENT_AMOUNT
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
        _assertAgentManagesTokens();

        vm.warp(vm.getBlockTimestamp() + MAX_SECONDS_IN_MONTH);

        // 100 USDC in 6 decimals counts as 100e18 against the limit
        _topUpByMotion(
            topUpAllowedRecipients,
            _encodeTopUp(usdc, _single(recipients[1]), _amounts(100e6)),
            SPENT_AMOUNT
        );

        vm.prank(_trustedCaller(topUpAllowedRecipients));
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(
            topUpAllowedRecipients, _encodeTopUp(usdc, _single(recipients[1]), _amounts(1))
        );
    }

    // python: test_full_setup_happy_path
    function testFork_FullSetupHappyPath() external {
        _advanceToNextPeriod(PERIOD_DURATION_MONTHS);

        _deployFullSetup();

        _addRecipientByMotion(recipients[0], titles[0]);

        // 50 USDC in 6 decimals counts as 50e18 against the limit
        _topUpByMotion(
            topUpAllowedRecipients, _encodeTopUp(usdc, _recipients(1), _amounts(50e6)), SPENT_AMOUNT
        );

        _removeRecipientByMotion(recipients[0]);

        assertFalse(
            allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "recipient#2 not allowed"
        );

        vm.prank(agent);
        allowedRecipientsRegistry.addRecipient(recipients[1], titles[1]);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipients[1]), "recipient#2 added");

        _assertAgentManagesTokens();

        vm.warp(vm.getBlockTimestamp() + MAX_SECONDS_IN_MONTH);

        _topUpByMotion(
            topUpAllowedRecipients,
            _encodeTopUp(dai, _single(recipients[1]), _amounts(100e18)),
            SPENT_AMOUNT
        );

        vm.prank(trustedCaller);
        vm.expectRevert(bytes(SUM_EXCEEDS_SPENDABLE_BALANCE));
        easyTrack.createMotion(
            topUpAllowedRecipients, _encodeTopUp(dai, _single(recipients[1]), _amounts(1))
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
        vm.recordLogs();

        builder.deploySingleRecipientTopUpOnlySetup(
            recipients[0], titles[0], _tokens(), LIMIT, PERIOD_DURATION_MONTHS, SPENT_AMOUNT
        );

        Vm.Log[] memory logs = vm.getRecordedLogs();
        allowedRecipientsRegistry = IAllowedRecipientsRegistry(
            _deployedAddress(
                logs, IAllowedRecipientsFactory.AllowedRecipientsRegistryDeployed.selector
            )
        );
        allowedTokensRegistry = IAllowedTokensRegistry(
            _deployedAddress(logs, IAllowedRecipientsFactory.AllowedTokensRegistryDeployed.selector)
        );
        topUpAllowedRecipients = _deployedAddress(
            logs, IAllowedRecipientsFactory.TopUpAllowedRecipientsDeployed.selector
        );

        _labelDeployment();
        _registerTopUpFactory(topUpAllowedRecipients);
    }

    /// @dev python: full_setup
    function _deployFullSetup() private {
        vm.recordLogs();

        builder.deployFullSetup(
            trustedCaller,
            LIMIT,
            PERIOD_DURATION_MONTHS,
            _tokens(),
            new address[](0),
            new string[](0),
            SPENT_AMOUNT
        );

        Vm.Log[] memory logs = vm.getRecordedLogs();
        allowedRecipientsRegistry = IAllowedRecipientsRegistry(
            _deployedAddress(
                logs, IAllowedRecipientsFactory.AllowedRecipientsRegistryDeployed.selector
            )
        );
        allowedTokensRegistry = IAllowedTokensRegistry(
            _deployedAddress(logs, IAllowedRecipientsFactory.AllowedTokensRegistryDeployed.selector)
        );
        topUpAllowedRecipients = _deployedAddress(
            logs, IAllowedRecipientsFactory.TopUpAllowedRecipientsDeployed.selector
        );
        addAllowedRecipient =
            _deployedAddress(logs, IAllowedRecipientsFactory.AddAllowedRecipientDeployed.selector);
        removeAllowedRecipient = _deployedAddress(
            logs, IAllowedRecipientsFactory.RemoveAllowedRecipientDeployed.selector
        );

        _labelDeployment();
        vm.label(addAllowedRecipient, "AddAllowedRecipient");
        vm.label(removeAllowedRecipient, "RemoveAllowedRecipient");

        _registerAddFactory(addAllowedRecipient);
        _registerRemoveFactory(removeAllowedRecipient);
        _registerTopUpFactory(topUpAllowedRecipients);
    }

    /// @dev The contract a deployment event of the builder's factory reports, its second indexed
    ///      argument
    function _deployedAddress(Vm.Log[] memory logs, bytes32 selector)
        private
        view
        returns (address)
    {
        address factory = builder.factory();
        for (uint256 index; index < logs.length; ++index) {
            if (logs[index].emitter == factory && logs[index].topics[0] == selector) {
                return address(uint160(uint256(logs[index].topics[2])));
            }
        }

        revert("deployment event not found");
    }

    function _labelDeployment() private {
        vm.label(address(allowedRecipientsRegistry), "AllowedRecipientsRegistry");
        vm.label(address(allowedTokensRegistry), "AllowedTokensRegistry");
        vm.label(topUpAllowedRecipients, "TopUpAllowedRecipients");
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

    /// @dev The Agent removes DAI from the allowed tokens and adds it back
    function _assertAgentManagesTokens() private {
        assertTrue(allowedTokensRegistry.isTokenAllowed(dai), "DAI allowed");

        vm.prank(agent);
        allowedTokensRegistry.removeToken(dai);

        assertFalse(allowedTokensRegistry.isTokenAllowed(dai), "DAI removed");

        vm.prank(agent);
        allowedTokensRegistry.addToken(dai);

        assertTrue(allowedTokensRegistry.isTokenAllowed(dai), "DAI added back");
    }

    function _tokens() private view returns (address[] memory tokens) {
        tokens = new address[](2);
        tokens[0] = dai;
        tokens[1] = usdc;
    }
}
