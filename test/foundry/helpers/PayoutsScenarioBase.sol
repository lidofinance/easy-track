// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IntegrationTestAddresses} from "test/foundry/helpers/IntegrationTestAddresses.sol";
import {IEasyTrack} from "test/foundry/interfaces/EasyTrack.sol";
import {
    IBokkyPooBahsDateTimeContract,
    IERC20,
    IFinance,
    ILido,
    ILidoLocator
} from "test/foundry/interfaces/External.sol";
import {
    IAllowedRecipientsBuilder,
    IAllowedRecipientsBuilderSingleToken,
    IAllowedRecipientsRegistry,
    IAllowedTokensRegistry,
    ITopUpAllowedRecipients,
    ITopUpAllowedRecipientsSingleToken,
    ITrustedCaller
} from "test/foundry/interfaces/Payouts.sol";

/// @notice Harness for the allowed recipients payouts scenarios, the conftest fixtures of the
///         Brownie suite over `integration-test-addresses-<chain>.yaml`: the suite's Easy Track,
///         factory and builder, and per instance a registry with its add, remove and top-up
///         factories, each bound to the listed deployment or, where the file lists none, deployed
///         fresh through the builder from the `contracts` profile artifacts and registered in Easy
///         Track as the DAO Voting. Payouts go through the live Aragon Finance from the Agent, the
///         registries' admin. Period arithmetic goes through the deployed date-time contract the
///         registries use, so the scenarios warp to calendar periods, never to a duration. Two
///         flavors below bind the multi-token and the single-token contracts.
abstract contract PayoutsScenarioBase is EasyTrackScenarioBase {
    /// @dev A top-up motion's payout and the registry state its enactment must leave
    struct TopUp {
        address token;
        address[] to;
        uint256[] amounts;
        uint256 limit;
        uint256 periodDuration;
        /// @dev the sum of `amounts`, in token decimals
        uint256 spendingInTokens;
        /// @dev the normalized sum plus what the period already carried
        uint256 alreadySpent;
        uint256 spendable;
        uint256 agentBalanceBefore;
        uint256[] balancesBefore;
        /// @dev stETH only: the shares the payout moves from the Agent to the recipients
        uint256 agentSharesBefore;
        uint256 recipientsSharesBefore;
    }

    /// @dev python: MAX_SECONDS_IN_MONTH, how far the Brownie suite sleeps for "a month"
    uint256 internal constant MAX_SECONDS_IN_MONTH = 31 days;

    /// @dev python: STETH_ERROR_MARGIN_WEI, the rounding a stETH transfer may lose
    uint256 internal constant STETH_ERROR_MARGIN_WEI = 2;

    /// @dev python: allowed_recipients_default_params
    uint256 internal constant LIMIT = 100e18;
    uint256 internal constant PERIOD_DURATION_MONTHS = 1;
    uint256 internal constant SPENT_AMOUNT = 0;

    IFinance internal finance;
    address internal agent;
    address internal voting;
    IBokkyPooBahsDateTimeContract internal dateTime;
    ILido internal steth;

    address internal trustedCaller = makeAddr("trustedCaller");

    /// @dev python: recipients, the three `Recipient(address, title)` of the suite
    address[] internal recipients;
    string[] internal titles;

    /// @dev python: the `instances` of the suite, the `deployed_contracts` parameters
    IntegrationTestAddresses.Instance[] internal instances;

    IAllowedRecipientsRegistry internal allowedRecipientsRegistry;
    address internal addAllowedRecipient;
    address internal removeAllowedRecipient;
    address internal topUpAllowedRecipients;

    function setUp() public virtual {
        _forkAndInitialize();

        finance = IFinance(config.finance);
        agent = config.agent;
        voting = _voting();
        dateTime = IBokkyPooBahsDateTimeContract(config.dateTime);
        steth = ILido(ILidoLocator(config.locator).lido());

        vm.label(address(finance), "Finance");
        vm.label(voting, "Voting");
        vm.label(address(dateTime), "BokkyPooBahsDateTimeContract");
        vm.label(address(steth), "stETH");

        for (uint256 index; index < 3; ++index) {
            string memory title = string.concat("recipient#", vm.toString(index + 1));
            recipients.push(makeAddr(title));
            titles.push(title);
        }

        IntegrationTestAddresses.Suite memory suite =
            IntegrationTestAddresses.load(config.addresses, _suiteKey());
        for (uint256 index; index < suite.instances.length; ++index) {
            instances.push(suite.instances[index]);
        }

        _bindEasyTrack(suite.easyTrack);
        _bindBuilder(suite);
    }

    // --- flavor hooks ---

    /// @dev The suite's key in the addresses file
    function _suiteKey() internal pure virtual returns (string memory);

    /// @dev python: allowed_recipients_factory and allowed_recipients_builder, the suite's or fresh
    function _bindBuilder(IntegrationTestAddresses.Suite memory suite) internal virtual;

    /// @dev python: the registry fixture's deployment branch, a fresh registry with the default
    ///      params, the multi-token flavor with a fresh tokens registry
    function _deployRegistry() internal virtual;

    /// @dev python: the factory fixtures' deployment branches, through the flavor's builder with
    ///      `trustedCaller` over the instance's registry
    function _deployAddFactory() internal virtual returns (address);

    function _deployRemoveFactory() internal virtual returns (address);

    function _deployTopUpFactory() internal virtual returns (address);

    /// @dev The token, recipients and amounts a top-up motion of `factory` carries
    function _decodeTopUp(address factory, bytes memory callData)
        internal
        view
        virtual
        returns (address token, address[] memory to, uint256[] memory amounts);

    /// @dev `amount` of `token` in the 18 decimals the limits are kept in
    function _normalizeAmount(address token, uint256 amount) internal view virtual returns (uint256);

    // --- the suite's and the instance's contracts, bound or deployed as the fixtures do ---

    /// @dev python: easy_track. The suite's deployed Easy Track, or a fresh one with Voting as
    ///      admin. Either way its executor gets `CREATE_PAYMENTS_ROLE` on Finance, the deployed one
    ///      replacing the parameterized grant it holds on-chain with a plain one.
    function _bindEasyTrack(address deployed) private {
        if (deployed == address(0)) {
            _deployEasyTrack(voting);
        } else {
            easyTrack = IEasyTrack(deployed);
            evmScriptExecutor = easyTrack.evmScriptExecutor();
        }

        _grantPermission(evmScriptExecutor, address(finance), finance.CREATE_PAYMENTS_ROLE());
    }

    /// @dev python: the registry and factory fixtures of `deployed_contracts[name]`. Skips the
    ///      suite when the chain's addresses file lists no such instance, as pytest collects none.
    function _bindInstance(string memory name) internal {
        (bool found, IntegrationTestAddresses.Instance memory instance) = _instance(name);
        vm.skip(!found, string.concat("no \"", name, "\" instance in ", config.addresses));

        if (instance.registry == address(0)) {
            _deployRegistry();
        } else {
            allowedRecipientsRegistry = IAllowedRecipientsRegistry(instance.registry);
        }

        vm.label(address(allowedRecipientsRegistry), "AllowedRecipientsRegistry");

        _grantListRole(allowedRecipientsRegistry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE());
        _grantListRole(allowedRecipientsRegistry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE());

        // Reset spending for deployed registries so tests start with a clean slate
        vm.prank(agent);
        allowedRecipientsRegistry.unsafeSetSpentAmount(0);

        addAllowedRecipient = instance.addAllowedRecipient == address(0)
            ? _deployAddFactory()
            : instance.addAllowedRecipient;
        removeAllowedRecipient = instance.removeAllowedRecipient == address(0)
            ? _deployRemoveFactory()
            : instance.removeAllowedRecipient;
        topUpAllowedRecipients = instance.topUpAllowedRecipients == address(0)
            ? _deployTopUpFactory()
            : instance.topUpAllowedRecipients;

        vm.label(addAllowedRecipient, "AddAllowedRecipient");
        vm.label(removeAllowedRecipient, "RemoveAllowedRecipient");
        vm.label(topUpAllowedRecipients, "TopUpAllowedRecipients");

        _registerAddFactory(addAllowedRecipient);
        _registerRemoveFactory(removeAllowedRecipient);
        _registerTopUpFactory(topUpAllowedRecipients);
    }

    function _instance(string memory name)
        private
        view
        returns (bool found, IntegrationTestAddresses.Instance memory instance)
    {
        for (uint256 index; index < instances.length; ++index) {
            if (keccak256(bytes(instances[index].name)) == keccak256(bytes(name))) {
                return (true, instances[index]);
            }
        }
    }

    /// @dev The executor gets `role` on the registry from the Agent unless it holds it
    function _grantListRole(bytes32 role) private {
        if (allowedRecipientsRegistry.hasRole(role, evmScriptExecutor)) {
            return;
        }

        vm.prank(agent);
        allowedRecipientsRegistry.grantRole(role, evmScriptExecutor);
    }

    // --- factory registration, as the DAO vote that goes with a deployment ---

    function _registerAddFactory(address factory) internal {
        _registerFactoryIfMissing(
            factory,
            abi.encodePacked(
                allowedRecipientsRegistry, IAllowedRecipientsRegistry.addRecipient.selector
            )
        );
    }

    function _registerRemoveFactory(address factory) internal {
        _registerFactoryIfMissing(
            factory,
            abi.encodePacked(
                allowedRecipientsRegistry, IAllowedRecipientsRegistry.removeRecipient.selector
            )
        );
    }

    function _registerTopUpFactory(address factory) internal {
        _registerFactoryIfMissing(
            factory,
            abi.encodePacked(
                finance,
                IFinance.newImmediatePayment.selector,
                allowedRecipientsRegistry,
                IAllowedRecipientsRegistry.updateSpentAmount.selector
            )
        );
    }

    // --- motion drivers ---

    /// @dev python: add_allowed_recipient_by_motion
    function _addRecipientByMotion(address recipient, string memory title) internal {
        _enact(
            addAllowedRecipient, _trustedCaller(addAllowedRecipient), abi.encode(recipient, title)
        );

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipient), "recipient allowed");
    }

    /// @dev python: remove_allowed_recipient_by_motion
    function _removeRecipientByMotion(address recipient) internal {
        _enact(
            removeAllowedRecipient, _trustedCaller(removeAllowedRecipient), abi.encode(recipient)
        );

        assertFalse(allowedRecipientsRegistry.isRecipientAllowed(recipient), "recipient removed");
    }

    /// @dev python: create_top_up_allowed_recipients_motion
    function _createTopUpMotion(address factory, bytes memory callData) internal returns (uint256) {
        return _createMotion(factory, _trustedCaller(factory), callData);
    }

    /// @dev python: top_up_allowed_recipient_by_motion
    function _topUpByMotion(address factory, bytes memory callData, uint256 spentAmount) internal {
        _enactTopUpMotion(_createTopUpMotion(factory, callData), callData, spentAmount);
    }

    /// @dev python: enact_top_up_allowed_recipient_motion_by_creation_tx with
    ///      check_top_up_motion_enactment. Enacts the motion once it has ended and asserts the
    ///      limits state, the balances and the `SpendableAmountChanged` event of the period the
    ///      enactment falls in. `spentAmount` is what the period already carried.
    function _enactTopUpMotion(uint256 motionId, bytes memory callData, uint256 spentAmount)
        internal
    {
        IEasyTrack.Motion memory motion = easyTrack.getMotion(motionId);
        TopUp memory topUp = _topUp(motion.evmScriptFactory, callData, spentAmount);

        if (vm.getBlockTimestamp() < motion.startDate + motion.duration) {
            _passMotionDuration();
        }

        (uint256 periodStart, uint256 periodEnd) =
            _periodRange(topUp.periodDuration, vm.getBlockTimestamp());

        vm.expectEmit(address(allowedRecipientsRegistry));
        emit IAllowedRecipientsRegistry.SpendableAmountChanged(
            topUp.alreadySpent, topUp.spendable, periodStart, periodEnd
        );

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        _assertTopUp(topUp);
    }

    /// @dev What a top-up motion of `factory` spends and leaves, over the registry's current
    ///      limit and the balances before enactment
    function _topUp(address factory, bytes memory callData, uint256 spentAmount)
        private
        view
        returns (TopUp memory topUp)
    {
        (topUp.token, topUp.to, topUp.amounts) = _decodeTopUp(factory, callData);
        (topUp.limit, topUp.periodDuration) = allowedRecipientsRegistry.getLimitParameters();
        topUp.spendingInTokens = _sum(topUp.amounts);
        topUp.alreadySpent = _normalizeAmount(topUp.token, topUp.spendingInTokens) + spentAmount;
        topUp.spendable = topUp.limit - topUp.alreadySpent;
        topUp.agentBalanceBefore = IERC20(topUp.token).balanceOf(agent);
        topUp.balancesBefore = _balances(topUp.token, topUp.to);

        if (topUp.token == address(steth)) {
            topUp.agentSharesBefore = steth.sharesOf(agent);
            topUp.recipientsSharesBefore = _shares(topUp.to);
        }
    }

    /// @dev python: check_top_up_motion_enactment, the limits state and the balances after
    ///      enactment. A stETH balance may lose `STETH_ERROR_MARGIN_WEI` to rounding, so stETH
    ///      payouts are checked in shares as well.
    function _assertTopUp(TopUp memory topUp) private view {
        assertTrue(
            allowedRecipientsRegistry.isUnderSpendableBalance(topUp.spendable, 0),
            "isUnderSpendableBalance spendable"
        );
        assertTrue(
            allowedRecipientsRegistry.isUnderSpendableBalance(
                topUp.limit, topUp.periodDuration * MAX_SECONDS_IN_MONTH
            ),
            "isUnderSpendableBalance limit"
        );

        (uint256 alreadySpentAmount, uint256 spendableBalanceInPeriod,,) =
            allowedRecipientsRegistry.getPeriodState();
        assertEq(alreadySpentAmount, topUp.alreadySpent, "_alreadySpentAmount");
        assertEq(spendableBalanceInPeriod, topUp.spendable, "_spendableBalanceInPeriod");

        uint256 agentBalanceExpected = topUp.agentBalanceBefore - topUp.spendingInTokens;
        if (topUp.token == address(steth)) {
            assertApproxEqAbs(
                IERC20(topUp.token).balanceOf(agent),
                agentBalanceExpected,
                STETH_ERROR_MARGIN_WEI,
                "agent balance"
            );

            uint256 agentSharesAfter = steth.sharesOf(agent);
            uint256 recipientsSharesAfter = _shares(topUp.to);
            assertGe(topUp.agentSharesBefore, agentSharesAfter, "agent shares");
            assertEq(
                topUp.agentSharesBefore - agentSharesAfter,
                recipientsSharesAfter - topUp.recipientsSharesBefore,
                "shares moved"
            );
        } else {
            assertEq(IERC20(topUp.token).balanceOf(agent), agentBalanceExpected, "agent balance");
        }

        for (uint256 index; index < topUp.to.length; ++index) {
            uint256 balanceExpected = topUp.balancesBefore[index] + topUp.amounts[index];
            string memory message = string.concat("recipient balance ", vm.toString(index));
            if (topUp.token == address(steth)) {
                assertApproxEqAbs(
                    IERC20(topUp.token).balanceOf(topUp.to[index]),
                    balanceExpected,
                    STETH_ERROR_MARGIN_WEI,
                    message
                );
            } else {
                assertEq(IERC20(topUp.token).balanceOf(topUp.to[index]), balanceExpected, message);
            }
        }
    }

    function _trustedCaller(address factory) internal view returns (address) {
        return ITrustedCaller(factory).trustedCaller();
    }

    // --- calendar periods, through the date-time contract the registry computes them with ---

    /// @dev python: calc_period_range. The period of `periodDuration` months `timestamp` falls in
    function _periodRange(uint256 periodDuration, uint256 timestamp)
        internal
        view
        returns (uint256 periodStart, uint256 periodEnd)
    {
        (uint256 year, uint256 month,) = dateTime.timestampToDate(timestamp);
        uint256 firstMonth = ((month - 1) / periodDuration) * periodDuration + 1;

        periodStart = dateTime.timestampFromDate(year, firstMonth, 1);
        periodEnd = dateTime.addMonths(periodStart, periodDuration);
    }

    /// @dev python: advance_chain_time_to_beginning_of_the_next_period
    function _advanceToNextPeriod(uint256 periodDuration) internal {
        (, uint256 periodEnd) = _periodRange(periodDuration, vm.getBlockTimestamp());

        vm.warp(periodEnd);
    }

    /// @dev python: advance_chain_time_to_middle_of_the_next_period
    function _advanceToMiddleOfNextPeriod(uint256 periodDuration) internal {
        _advanceToNextPeriod(periodDuration);

        (uint256 periodStart, uint256 periodEnd) =
            _periodRange(periodDuration, vm.getBlockTimestamp());

        vm.warp(periodStart + (periodEnd - periodStart) / 2);
    }

    /// @dev python: advance_chain_time_to_n_seconds_before_current_period_end
    function _advanceToBeforePeriodEnd(uint256 periodDuration, uint256 secondsBefore) internal {
        (, uint256 periodEnd) = _periodRange(periodDuration, vm.getBlockTimestamp());

        assertGt(periodEnd - vm.getBlockTimestamp(), secondsBefore, "seconds left in the period");

        vm.warp(periodEnd - secondsBefore);
    }

    // --- arrays ---

    function _recipients(uint256 count) internal view returns (address[] memory to) {
        to = new address[](count);
        for (uint256 index; index < count; ++index) {
            to[index] = recipients[index];
        }
    }

    function _single(address recipient) internal pure returns (address[] memory to) {
        to = new address[](1);
        to[0] = recipient;
    }

    function _amounts(uint256 amount) internal pure returns (uint256[] memory amounts) {
        amounts = new uint256[](1);
        amounts[0] = amount;
    }

    function _amounts(uint256 first, uint256 second)
        internal
        pure
        returns (uint256[] memory amounts)
    {
        amounts = new uint256[](2);
        amounts[0] = first;
        amounts[1] = second;
    }

    function _sum(uint256[] memory amounts) internal pure returns (uint256 total) {
        for (uint256 index; index < amounts.length; ++index) {
            total += amounts[index];
        }
    }

    /// @dev python: get_balances
    function _balances(address token, address[] memory accounts)
        internal
        view
        returns (uint256[] memory balances)
    {
        balances = new uint256[](accounts.length);
        for (uint256 index; index < accounts.length; ++index) {
            balances[index] = IERC20(token).balanceOf(accounts[index]);
        }
    }

    /// @dev The stETH shares of `accounts` together
    function _shares(address[] memory accounts) private view returns (uint256 total) {
        for (uint256 index; index < accounts.length; ++index) {
            total += steth.sharesOf(accounts[index]);
        }
    }

    /// @dev python: access_revert_message. The OpenZeppelin v4 AccessControl reason, the account
    ///      lowercased as `Strings.toHexString` prints it
    function _accessRevertMessage(address account, bytes32 role)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(
            "AccessControl: account ",
            vm.toLowercase(vm.toString(account)),
            " is missing role ",
            vm.toString(role)
        );
    }
}

/// @notice The multi-token flavor: `AllowedRecipientsBuilder` over `AllowedRecipientsFactory`,
///         paying DAI and USDC through an `AllowedTokensRegistry`. Top-up calldata is
///         `(address token, address[] recipients, uint256[] amounts)`.
abstract contract MultiTokenPayoutsScenarioBase is PayoutsScenarioBase {
    IAllowedRecipientsBuilder internal builder;
    IAllowedTokensRegistry internal allowedTokensRegistry;
    address internal dai;
    address internal usdc;

    function setUp() public virtual override {
        super.setUp();

        dai = config.dai;
        usdc = config.usdc;

        vm.label(dai, "DAI");
        vm.label(usdc, "USDC");
    }

    function _suiteKey() internal pure override returns (string memory) {
        return "multi_token";
    }

    function _bindBuilder(IntegrationTestAddresses.Suite memory suite) internal override {
        address factory = suite.factory == address(0)
            ? _deployArtifact("AllowedRecipientsFactory", "")
            : suite.factory;
        builder = suite.builder == address(0)
            ? IAllowedRecipientsBuilder(
                _deployArtifact(
                    "AllowedRecipientsBuilder",
                    abi.encode(factory, agent, easyTrack, finance, dateTime)
                )
            )
            : IAllowedRecipientsBuilder(suite.builder);
        allowedTokensRegistry = IAllowedTokensRegistry(suite.tokensRegistry);

        vm.label(factory, "AllowedRecipientsFactory");
        vm.label(address(builder), "AllowedRecipientsBuilder");

        if (suite.tokensRegistry != address(0)) {
            vm.label(suite.tokensRegistry, "AllowedTokensRegistry");
        }
    }

    function _deployRegistry() internal override {
        allowedRecipientsRegistry = builder.deployAllowedRecipientsRegistry(
            LIMIT, PERIOD_DURATION_MONTHS, new address[](0), new string[](0), SPENT_AMOUNT, true
        );
        allowedTokensRegistry = builder.deployAllowedTokensRegistry(new address[](0));

        vm.label(address(allowedTokensRegistry), "AllowedTokensRegistry");
    }

    function _deployAddFactory() internal override returns (address) {
        return address(
            builder.deployAddAllowedRecipient(trustedCaller, address(allowedRecipientsRegistry))
        );
    }

    function _deployRemoveFactory() internal override returns (address) {
        return address(
            builder.deployRemoveAllowedRecipient(trustedCaller, address(allowedRecipientsRegistry))
        );
    }

    function _deployTopUpFactory() internal override returns (address) {
        return address(
            builder.deployTopUpAllowedRecipients(
                trustedCaller, address(allowedRecipientsRegistry), address(allowedTokensRegistry)
            )
        );
    }

    function _decodeTopUp(address factory, bytes memory callData)
        internal
        pure
        override
        returns (address token, address[] memory to, uint256[] memory amounts)
    {
        return ITopUpAllowedRecipients(factory).decodeEVMScriptCallData(callData);
    }

    function _normalizeAmount(address token, uint256 amount)
        internal
        view
        override
        returns (uint256)
    {
        return allowedTokensRegistry.normalizeAmount(amount, token);
    }

    function _encodeTopUp(address token, address[] memory to, uint256[] memory amounts)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encode(token, to, amounts);
    }

    /// @dev python: add_allowed_token, a no-op when the token is already allowed
    function _allowToken(address token) internal {
        _grantTokenRole(allowedTokensRegistry.ADD_TOKEN_TO_ALLOWED_LIST_ROLE());

        if (allowedTokensRegistry.isTokenAllowed(token)) {
            return;
        }

        vm.prank(agent);
        allowedTokensRegistry.addToken(token);

        assertTrue(allowedTokensRegistry.isTokenAllowed(token), "token allowed");
    }

    /// @dev python: remove_allowed_token, a no-op when the token is not allowed
    function _disallowToken(address token) internal {
        _grantTokenRole(allowedTokensRegistry.REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE());

        if (!allowedTokensRegistry.isTokenAllowed(token)) {
            return;
        }

        vm.prank(agent);
        allowedTokensRegistry.removeToken(token);

        assertFalse(allowedTokensRegistry.isTokenAllowed(token), "token removed");
    }

    /// @dev The Agent gets `role` on the tokens registry unless it holds it, from itself when it
    ///      is the registry's admin, else from Voting
    function _grantTokenRole(bytes32 role) private {
        if (allowedTokensRegistry.hasRole(role, agent)) {
            return;
        }

        address admin = allowedTokensRegistry.hasRole(
            allowedTokensRegistry.DEFAULT_ADMIN_ROLE(), agent
        )
            ? agent
            : voting;

        vm.prank(admin);
        allowedTokensRegistry.grantRole(role, agent);
    }

    /// @dev python: ensure_agent_dai_balance, which mints from the DAI ward
    function _ensureAgentDaiBalance(uint256 amount) internal {
        if (IERC20(dai).balanceOf(agent) >= amount) {
            return;
        }

        deal(dai, agent, amount);
    }
}

/// @notice The single-token flavor: `AllowedRecipientsBuilderSingleToken` over
///         `AllowedRecipientsFactorySingleToken`, a fresh top-up factory paying LDO, a listed one
///         its own `token`. Top-up calldata is `(address[] recipients, uint256[] amounts)`.
abstract contract SingleTokenPayoutsScenarioBase is PayoutsScenarioBase {
    IAllowedRecipientsBuilderSingleToken internal builder;
    address internal ldo;

    function setUp() public virtual override {
        super.setUp();

        ldo = easyTrack.governanceToken();

        vm.label(ldo, "LDO");
    }

    function _suiteKey() internal pure override returns (string memory) {
        return "single_token";
    }

    function _bindBuilder(IntegrationTestAddresses.Suite memory suite) internal override {
        address factory = suite.factory == address(0)
            ? _deployArtifact("AllowedRecipientsFactorySingleToken", "")
            : suite.factory;
        builder = suite.builder == address(0)
            ? IAllowedRecipientsBuilderSingleToken(
                _deployArtifact(
                    "AllowedRecipientsBuilderSingleToken",
                    abi.encode(factory, agent, easyTrack, finance, dateTime)
                )
            )
            : IAllowedRecipientsBuilderSingleToken(suite.builder);

        vm.label(factory, "AllowedRecipientsFactorySingleToken");
        vm.label(address(builder), "AllowedRecipientsBuilderSingleToken");
    }

    function _deployRegistry() internal override {
        allowedRecipientsRegistry = builder.deployAllowedRecipientsRegistry(
            LIMIT, PERIOD_DURATION_MONTHS, new address[](0), new string[](0), SPENT_AMOUNT, true
        );
    }

    function _deployAddFactory() internal override returns (address) {
        return address(
            builder.deployAddAllowedRecipient(trustedCaller, address(allowedRecipientsRegistry))
        );
    }

    function _deployRemoveFactory() internal override returns (address) {
        return address(
            builder.deployRemoveAllowedRecipient(trustedCaller, address(allowedRecipientsRegistry))
        );
    }

    function _deployTopUpFactory() internal override returns (address) {
        return address(
            builder.deployTopUpAllowedRecipients(
                trustedCaller, address(allowedRecipientsRegistry), ldo
            )
        );
    }

    function _decodeTopUp(address factory, bytes memory callData)
        internal
        view
        override
        returns (address token, address[] memory to, uint256[] memory amounts)
    {
        token = ITopUpAllowedRecipientsSingleToken(factory).token();
        (to, amounts) =
            ITopUpAllowedRecipientsSingleToken(factory).decodeEVMScriptCallData(callData);
    }

    function _normalizeAmount(address, uint256 amount) internal pure override returns (uint256) {
        return amount;
    }

    function _encodeTopUp(address[] memory to, uint256[] memory amounts)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encode(to, amounts);
    }

    /// @dev python: ensure_agent_token_balance. Stakes the shortfall for stETH from the Agent, any
    ///      other token the Agent must already hold.
    function _ensureAgentTokenBalance(uint256 requested) internal {
        address token = ITopUpAllowedRecipientsSingleToken(topUpAllowedRecipients).token();
        uint256 balance = IERC20(token).balanceOf(agent);
        if (balance >= requested) {
            return;
        }

        uint256 shortfall = requested - balance;
        assertEq(
            token,
            address(steth),
            string.concat(
                "Agent is ",
                vm.toString(shortfall),
                " wei short of ",
                vm.toString(token),
                " and only stETH can be funded"
            )
        );

        uint256 stake = shortfall + STETH_ERROR_MARGIN_WEI;
        vm.deal(agent, agent.balance + stake);

        vm.prank(agent);
        steth.submit{value: stake}(address(0));

        assertGe(
            IERC20(token).balanceOf(agent), requested, "Error when trying to stake ETH for agent"
        );
    }
}
