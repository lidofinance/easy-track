// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import {
    AllowedRecipientsBuilder,
    IAllowedRecipientsFactory,
    IAddAllowedRecipient,
    IRemoveAllowedRecipient,
    ITopUpAllowedRecipients
} from "contracts/payouts/multi-token/AllowedRecipientsBuilder.sol";
import {AllowedRecipientsFactory} from "contracts/payouts/multi-token/AllowedRecipientsFactory.sol";
import {
    IAllowedRecipientsRegistry
} from "contracts/payouts/multi-token/interfaces/IAllowedRecipientsRegistry.sol";
import {
    IAllowedTokensRegistry
} from "contracts/payouts/multi-token/interfaces/IAllowedTokensRegistry.sol";
import {EasyTrack} from "contracts/EasyTrack.sol";
import {EVMScriptExecutor} from "contracts/EVMScriptExecutor.sol";
import {IEasyTrack} from "contracts/interfaces/IEasyTrack.sol";
import {Constants} from "test/foundry/unit/helpers/Constants.sol";
import {
    BokkyPooBahsDateTimeContract
} from "test/foundry/unit/stubs/BokkyPooBahsDateTimeContract.sol";
import {CallsScriptStub} from "test/foundry/unit/stubs/CallsScriptStub.sol";
import {MiniMeTokenStub} from "test/foundry/unit/stubs/MiniMeTokenStub.sol";

contract AllowedRecipientsBuilderMultiTokenTest is Test {
    // python: module role constants
    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 internal constant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE");
    bytes32 internal constant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE");
    bytes32 internal constant SET_PARAMETERS_ROLE = keccak256("SET_PARAMETERS_ROLE");
    bytes32 internal constant UPDATE_SPENT_AMOUNT_ROLE = keccak256("UPDATE_SPENT_AMOUNT_ROLE");
    bytes32 internal constant ADD_TOKEN_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_TOKEN_TO_ALLOWED_LIST_ROLE");
    bytes32 internal constant REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE");

    /// @dev Topics of the factory events the full setups are read back through, solc 0.8.6 has
    /// no `Event.selector`
    bytes32 internal constant ALLOWED_RECIPIENTS_REGISTRY_DEPLOYED = keccak256(
        "AllowedRecipientsRegistryDeployed(address,address,address,address[],address[],address[],address[],address)"
    );
    bytes32 internal constant ALLOWED_TOKENS_REGISTRY_DEPLOYED =
        keccak256("AllowedTokensRegistryDeployed(address,address,address,address[],address[])");
    bytes32 internal constant TOP_UP_ALLOWED_RECIPIENTS_DEPLOYED = keccak256(
        "TopUpAllowedRecipientsDeployed(address,address,address,address,address,address,address)"
    );
    bytes32 internal constant ADD_ALLOWED_RECIPIENT_DEPLOYED =
        keccak256("AddAllowedRecipientDeployed(address,address,address,address)");
    bytes32 internal constant REMOVE_ALLOWED_RECIPIENT_DEPLOYED =
        keccak256("RemoveAllowedRecipientDeployed(address,address,address,address)");

    uint256 internal constant LIMIT = 1 ether;
    uint256 internal constant PERIOD_DURATION_MONTHS = 1;
    uint256 internal constant SPENT_AMOUNT = 1e10;

    // python: the literals of test_deploy_full_setup
    address internal constant FULL_SETUP_TRUSTED_CALLER =
        0x3eaE0B337413407FB3C65324735D797ddc7E071D;
    uint256 internal constant FULL_SETUP_LIMIT = 10_000 ether;
    uint256 internal constant FULL_SETUP_SPENT_AMOUNT = 0;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");
    address internal agent = makeAddr("agent");
    address internal finance = makeAddr("finance");
    address internal usdc = makeAddr("usdc");
    address internal trustedCaller = makeAddr("trustedCaller");
    address internal recipient = makeAddr("recipient");
    address internal secondRecipient = makeAddr("secondRecipient");

    /// @dev python: accounts[4], an EOA the single factory deployments are wired to as a registry
    address internal recipientsRegistryStandIn = makeAddr("recipientsRegistryStandIn");
    address internal tokensRegistryStandIn = makeAddr("tokensRegistryStandIn");

    MiniMeTokenStub internal ldo;
    EasyTrack internal easyTrack;
    EVMScriptExecutor internal evmScriptExecutor;
    BokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;
    AllowedRecipientsFactory internal allowedRecipientsFactory;
    AllowedRecipientsBuilder internal allowedRecipientsBuilder;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event TopUpAllowedRecipientsDeployed(
        address indexed creator,
        address indexed topUpAllowedRecipients,
        address trustedCaller,
        address allowedRecipientsRegistry,
        address allowedTokenssRegistry,
        address finance,
        address easyTrack
    );
    event AddAllowedRecipientDeployed(
        address indexed creator,
        address indexed addAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );
    event RemoveAllowedRecipientDeployed(
        address indexed creator,
        address indexed removeAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    function setUp() public {
        bokkyPooBahsDateTimeContract = new BokkyPooBahsDateTimeContract();

        vm.startPrank(owner);
        ldo = new MiniMeTokenStub();
        CallsScriptStub callsScript = new CallsScriptStub();
        easyTrack = new EasyTrack(
            address(ldo),
            voting,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );
        evmScriptExecutor = new EVMScriptExecutor(address(callsScript), address(easyTrack));
        vm.stopPrank();

        vm.prank(voting);
        easyTrack.setEVMScriptExecutor(address(evmScriptExecutor));

        vm.startPrank(owner);
        allowedRecipientsFactory = new AllowedRecipientsFactory();
        allowedRecipientsBuilder = new AllowedRecipientsBuilder(
            IAllowedRecipientsFactory(address(allowedRecipientsFactory)),
            agent,
            IEasyTrack(address(easyTrack)),
            finance,
            address(bokkyPooBahsDateTimeContract)
        );
        vm.stopPrank();

        vm.label(address(easyTrack), "easyTrack");
        vm.label(address(evmScriptExecutor), "evmScriptExecutor");
        vm.label(address(bokkyPooBahsDateTimeContract), "bokkyPooBahsDateTimeContract");
        vm.label(address(allowedRecipientsFactory), "allowedRecipientsFactory");
        vm.label(address(allowedRecipientsBuilder), "allowedRecipientsBuilder");
    }

    // python: test_builder_constructor_params
    function test_BuilderConstructorParams() external view {
        assertEq(
            address(allowedRecipientsBuilder.factory()),
            address(allowedRecipientsFactory),
            "factory"
        );
        assertEq(allowedRecipientsBuilder.admin(), agent, "admin");
        assertEq(allowedRecipientsBuilder.finance(), finance, "finance");
        assertEq(address(allowedRecipientsBuilder.easyTrack()), address(easyTrack), "easyTrack");
        assertEq(
            allowedRecipientsBuilder.bokkyPooBahsDateTimeContract(),
            address(bokkyPooBahsDateTimeContract),
            "bokkyPooBahsDateTimeContract"
        );
        assertEq(
            allowedRecipientsBuilder.evmScriptExecutor(),
            address(evmScriptExecutor),
            "evmScriptExecutor"
        );
    }

    // python: test_deploy_top_up_allowed_recipients
    function test_DeploysTopUpAllowedRecipients() external {
        address expectedTopUpAllowedRecipients = _nextFactoryDeployment();

        vm.expectEmit(address(allowedRecipientsFactory));
        emit TopUpAllowedRecipientsDeployed(
            address(allowedRecipientsBuilder),
            expectedTopUpAllowedRecipients,
            trustedCaller,
            recipientsRegistryStandIn,
            tokensRegistryStandIn,
            finance,
            address(easyTrack)
        );

        vm.prank(stranger);
        ITopUpAllowedRecipients topUpAllowedRecipients =
            allowedRecipientsBuilder.deployTopUpAllowedRecipients(
                trustedCaller, recipientsRegistryStandIn, tokensRegistryStandIn
            );

        assertEq(
            topUpAllowedRecipients.allowedRecipientsRegistry(),
            recipientsRegistryStandIn,
            "allowedRecipientsRegistry"
        );
        assertEq(
            topUpAllowedRecipients.allowedTokensRegistry(),
            tokensRegistryStandIn,
            "allowedTokensRegistry"
        );
        assertEq(topUpAllowedRecipients.trustedCaller(), trustedCaller, "trustedCaller");
        assertEq(topUpAllowedRecipients.finance(), finance, "finance");
        assertEq(address(topUpAllowedRecipients.easyTrack()), address(easyTrack), "easyTrack");
    }

    // python: test_deploy_add_allowed_recipient
    function test_DeploysAddAllowedRecipient() external {
        address expectedAddAllowedRecipient = _nextFactoryDeployment();

        vm.expectEmit(address(allowedRecipientsFactory));
        emit AddAllowedRecipientDeployed(
            address(allowedRecipientsBuilder),
            expectedAddAllowedRecipient,
            trustedCaller,
            recipientsRegistryStandIn
        );

        vm.prank(stranger);
        IAddAllowedRecipient addAllowedRecipient = allowedRecipientsBuilder.deployAddAllowedRecipient(
            trustedCaller, recipientsRegistryStandIn
        );

        assertEq(
            addAllowedRecipient.allowedRecipientsRegistry(),
            recipientsRegistryStandIn,
            "allowedRecipientsRegistry"
        );
        assertEq(addAllowedRecipient.trustedCaller(), trustedCaller, "trustedCaller");
    }

    // python: test_deploy_remove_allowed_recipient
    function test_DeploysRemoveAllowedRecipient() external {
        address expectedRemoveAllowedRecipient = _nextFactoryDeployment();

        vm.expectEmit(address(allowedRecipientsFactory));
        emit RemoveAllowedRecipientDeployed(
            address(allowedRecipientsBuilder),
            expectedRemoveAllowedRecipient,
            trustedCaller,
            recipientsRegistryStandIn
        );

        vm.prank(stranger);
        IRemoveAllowedRecipient removeAllowedRecipient =
            allowedRecipientsBuilder.deployRemoveAllowedRecipient(
                trustedCaller, recipientsRegistryStandIn
            );

        assertEq(
            removeAllowedRecipient.allowedRecipientsRegistry(),
            recipientsRegistryStandIn,
            "allowedRecipientsRegistry"
        );
        assertEq(removeAllowedRecipient.trustedCaller(), trustedCaller, "trustedCaller");
    }

    // python: test_deploy_allowed_recipients_registry
    function test_DeploysAllowedRecipientsRegistry() external {
        address[] memory recipients = _addresses(recipient, secondRecipient);

        vm.prank(stranger);
        IAllowedRecipientsRegistry registry =
            allowedRecipientsBuilder.deployAllowedRecipientsRegistry(
                LIMIT, PERIOD_DURATION_MONTHS, recipients, _titles(), SPENT_AMOUNT, true
            );

        _assertAllowedRecipients(registry, recipients, LIMIT, SPENT_AMOUNT);
        _assertRecipientsRegistryRoles(registry, true);
    }

    // python: test_deploy_allowed_tokens_registry
    function test_DeploysAllowedTokensRegistry() external {
        address[] memory tokens = _addresses(address(ldo), usdc);

        vm.prank(stranger);
        IAllowedTokensRegistry registry =
            allowedRecipientsBuilder.deployAllowedTokensRegistry(tokens);

        _assertAllowedTokens(registry, tokens);
        _assertTokensRegistryRoles(registry);
    }

    // python: test_deploy_recipients_registry_reverts_recipients_length
    function test_RevertWhen_RecipientsRegistryRecipientsLengthMismatch() external {
        string[] memory titles = new string[](1);
        titles[0] = "account 3";

        vm.prank(stranger);
        vm.expectRevert("Recipients data length mismatch");
        allowedRecipientsBuilder.deployAllowedRecipientsRegistry(
            LIMIT,
            PERIOD_DURATION_MONTHS,
            _addresses(recipient, secondRecipient),
            titles,
            SPENT_AMOUNT,
            false
        );
    }

    // python: test_deploy_recipients_registry_reverts_spentAmount_gt_limit
    function test_RevertWhen_RecipientsRegistrySpentAmountExceedsLimit() external {
        uint256 limitBelowSpentAmount = 1e5;

        vm.prank(stranger);
        vm.expectRevert("_spentAmount must be lower or equal to limit");
        allowedRecipientsBuilder.deployAllowedRecipientsRegistry(
            limitBelowSpentAmount,
            PERIOD_DURATION_MONTHS,
            _addresses(recipient, secondRecipient),
            _titles(),
            SPENT_AMOUNT,
            false
        );
    }

    // python: test_deploy_full_setup
    function test_DeploysFullSetup() external {
        address[] memory tokens = _addresses(address(ldo));
        address[] memory recipients = _fullSetupRecipients();

        vm.recordLogs();

        vm.prank(stranger);
        allowedRecipientsBuilder.deployFullSetup(
            FULL_SETUP_TRUSTED_CALLER,
            FULL_SETUP_LIMIT,
            PERIOD_DURATION_MONTHS,
            tokens,
            recipients,
            _fullSetupTitles(),
            FULL_SETUP_SPENT_AMOUNT
        );

        Vm.Log[] memory logs = vm.getRecordedLogs();
        IAllowedRecipientsRegistry recipientsRegistry = IAllowedRecipientsRegistry(
            _deployedAddress(logs, ALLOWED_RECIPIENTS_REGISTRY_DEPLOYED)
        );
        IAllowedTokensRegistry tokensRegistry =
            IAllowedTokensRegistry(_deployedAddress(logs, ALLOWED_TOKENS_REGISTRY_DEPLOYED));
        ITopUpAllowedRecipients topUpAllowedRecipients =
            ITopUpAllowedRecipients(_deployedAddress(logs, TOP_UP_ALLOWED_RECIPIENTS_DEPLOYED));
        IAddAllowedRecipient addAllowedRecipient =
            IAddAllowedRecipient(_deployedAddress(logs, ADD_ALLOWED_RECIPIENT_DEPLOYED));
        IRemoveAllowedRecipient removeAllowedRecipient =
            IRemoveAllowedRecipient(_deployedAddress(logs, REMOVE_ALLOWED_RECIPIENT_DEPLOYED));

        assertEq(
            topUpAllowedRecipients.allowedRecipientsRegistry(),
            address(recipientsRegistry),
            "topUpAllowedRecipients.allowedRecipientsRegistry"
        );
        assertEq(
            topUpAllowedRecipients.trustedCaller(),
            FULL_SETUP_TRUSTED_CALLER,
            "topUpAllowedRecipients.trustedCaller"
        );
        assertEq(
            addAllowedRecipient.allowedRecipientsRegistry(),
            address(recipientsRegistry),
            "addAllowedRecipient.allowedRecipientsRegistry"
        );
        assertEq(
            addAllowedRecipient.trustedCaller(),
            FULL_SETUP_TRUSTED_CALLER,
            "addAllowedRecipient.trustedCaller"
        );
        assertEq(
            removeAllowedRecipient.allowedRecipientsRegistry(),
            address(recipientsRegistry),
            "removeAllowedRecipient.allowedRecipientsRegistry"
        );
        assertEq(
            removeAllowedRecipient.trustedCaller(),
            FULL_SETUP_TRUSTED_CALLER,
            "removeAllowedRecipient.trustedCaller"
        );

        _assertAllowedRecipients(
            recipientsRegistry, recipients, FULL_SETUP_LIMIT, FULL_SETUP_SPENT_AMOUNT
        );
        _assertRecipientsRegistryRoles(recipientsRegistry, true);
        _assertAllowedTokens(tokensRegistry, tokens);
        _assertTokensRegistryRoles(tokensRegistry);
    }

    // python: test_deploy_deploy_single_recipient_top_up_only_setup
    function test_DeploysSingleRecipientTopUpOnlySetup() external {
        address[] memory tokens = _addresses(address(ldo));

        vm.recordLogs();

        vm.prank(stranger);
        allowedRecipientsBuilder.deploySingleRecipientTopUpOnlySetup(
            recipient, "recipient", tokens, LIMIT, PERIOD_DURATION_MONTHS, SPENT_AMOUNT
        );

        Vm.Log[] memory logs = vm.getRecordedLogs();
        IAllowedRecipientsRegistry recipientsRegistry = IAllowedRecipientsRegistry(
            _deployedAddress(logs, ALLOWED_RECIPIENTS_REGISTRY_DEPLOYED)
        );
        IAllowedTokensRegistry tokensRegistry =
            IAllowedTokensRegistry(_deployedAddress(logs, ALLOWED_TOKENS_REGISTRY_DEPLOYED));
        ITopUpAllowedRecipients topUpAllowedRecipients =
            ITopUpAllowedRecipients(_deployedAddress(logs, TOP_UP_ALLOWED_RECIPIENTS_DEPLOYED));

        assertEq(
            topUpAllowedRecipients.allowedRecipientsRegistry(),
            address(recipientsRegistry),
            "allowedRecipientsRegistry"
        );

        _assertAllowedRecipients(recipientsRegistry, _addresses(recipient), LIMIT, SPENT_AMOUNT);
        _assertRecipientsRegistryRoles(recipientsRegistry, false);
        _assertAllowedTokens(tokensRegistry, tokens);
        _assertTokensRegistryRoles(tokensRegistry);
    }

    /// @dev The address of the factory's next `new`, so `expectEmit` can pin the deployed topic
    function _nextFactoryDeployment() private view returns (address) {
        return vm.computeCreateAddress(
            address(allowedRecipientsFactory), vm.getNonce(address(allowedRecipientsFactory))
        );
    }

    /// @dev python: tx.events[<name>][<deployed>]. The deployed address the factory emitted
    function _deployedAddress(Vm.Log[] memory logs, bytes32 eventTopic)
        private
        view
        returns (address)
    {
        for (uint256 i; i < logs.length; ++i) {
            if (
                logs[i].emitter == address(allowedRecipientsFactory)
                    && logs[i].topics[0] == eventTopic
            ) {
                return address(uint160(uint256(logs[i].topics[2])));
            }
        }

        revert("DEPLOYMENT_EVENT_NOT_FOUND");
    }

    function _addresses(address a) private pure returns (address[] memory addresses) {
        addresses = new address[](1);
        addresses[0] = a;
    }

    function _addresses(address a, address b) private pure returns (address[] memory addresses) {
        addresses = new address[](2);
        addresses[0] = a;
        addresses[1] = b;
    }

    /// @dev python: ["account 3", "account 4"]
    function _titles() private pure returns (string[] memory titles) {
        titles = new string[](2);
        titles[0] = "account 3";
        titles[1] = "account 4";
    }

    /// @dev python: the five recipients of test_deploy_full_setup
    function _fullSetupRecipients() private pure returns (address[] memory recipients) {
        recipients = new address[](5);
        recipients[0] = 0xbbe8dDEf5BF31b71Ff5DbE89635f9dB4DeFC667E;
        recipients[1] = 0x07fC01f46dC1348d7Ce43787b5Bbd52d8711a92D;
        recipients[2] = 0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1;
        recipients[3] = 0xDDFFac49946D1F6CE4d9CaF3B9C7d340d4848A1C;
        recipients[4] = 0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97;
    }

    /// @dev python: the five titles of test_deploy_full_setup
    function _fullSetupTitles() private pure returns (string[] memory titles) {
        titles = new string[](5);
        titles[0] = "Default Reward Program";
        titles[1] = "Happy";
        titles[2] = "Sergey'2 #add RewardProgram";
        titles[3] = "Jumpgate Test";
        titles[4] = "tester";
    }

    /// @dev The recipients, limit and spendable balance the Python reads off a deployed registry
    function _assertAllowedRecipients(
        IAllowedRecipientsRegistry registry,
        address[] memory recipients,
        uint256 limit,
        uint256 spentAmount
    ) private view {
        assertEq(
            registry.getAllowedRecipients().length,
            recipients.length,
            "getAllowedRecipients().length"
        );

        for (uint256 i; i < recipients.length; ++i) {
            assertTrue(registry.isRecipientAllowed(recipients[i]), "isRecipientAllowed");
        }

        (uint256 registryLimit, uint256 periodDurationMonths) = registry.getLimitParameters();
        assertEq(registryLimit, limit, "limit");
        assertEq(periodDurationMonths, PERIOD_DURATION_MONTHS, "periodDurationMonths");
        assertEq(registry.spendableBalance(), limit - spentAmount, "spendableBalance");
    }

    /// @dev The role matrix the Python asserts on every deployed recipients registry. The
    /// executor holds the add and remove roles only when the builder was asked to grant them
    function _assertRecipientsRegistryRoles(
        IAllowedRecipientsRegistry registry,
        bool grantedToEVMScriptExecutor
    ) private view {
        assertTrue(
            registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, agent),
            "agent ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE"
        );
        assertTrue(
            registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, agent),
            "agent REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE"
        );
        assertTrue(registry.hasRole(SET_PARAMETERS_ROLE, agent), "agent SET_PARAMETERS_ROLE");
        assertTrue(
            registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, agent), "agent UPDATE_SPENT_AMOUNT_ROLE"
        );
        assertTrue(registry.hasRole(DEFAULT_ADMIN_ROLE, agent), "agent DEFAULT_ADMIN_ROLE");

        address executor = address(evmScriptExecutor);
        assertEq(
            registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, executor),
            grantedToEVMScriptExecutor,
            "evmScriptExecutor ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE"
        );
        assertEq(
            registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, executor),
            grantedToEVMScriptExecutor,
            "evmScriptExecutor REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE"
        );
        assertTrue(
            registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, executor),
            "evmScriptExecutor UPDATE_SPENT_AMOUNT_ROLE"
        );
        assertFalse(
            registry.hasRole(SET_PARAMETERS_ROLE, executor), "evmScriptExecutor SET_PARAMETERS_ROLE"
        );
        assertFalse(
            registry.hasRole(DEFAULT_ADMIN_ROLE, executor), "evmScriptExecutor DEFAULT_ADMIN_ROLE"
        );

        address self = address(registry);
        assertFalse(
            registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, self),
            "registry ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE"
        );
        assertFalse(
            registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, self),
            "registry REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE"
        );
        assertFalse(registry.hasRole(SET_PARAMETERS_ROLE, self), "registry SET_PARAMETERS_ROLE");
        assertFalse(
            registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, self), "registry UPDATE_SPENT_AMOUNT_ROLE"
        );
        assertFalse(registry.hasRole(DEFAULT_ADMIN_ROLE, self), "registry DEFAULT_ADMIN_ROLE");
    }

    /// @dev The tokens the Python reads off a deployed tokens registry
    function _assertAllowedTokens(IAllowedTokensRegistry registry, address[] memory tokens)
        private
        view
    {
        for (uint256 i; i < tokens.length; ++i) {
            assertTrue(registry.isTokenAllowed(tokens[i]), "isTokenAllowed");
        }

        assertEq(registry.getAllowedTokens(), tokens, "getAllowedTokens");
    }

    /// @dev The role matrix the Python asserts on every deployed tokens registry
    function _assertTokensRegistryRoles(IAllowedTokensRegistry registry) private view {
        assertTrue(registry.hasRole(DEFAULT_ADMIN_ROLE, agent), "agent DEFAULT_ADMIN_ROLE");
        assertTrue(
            registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, agent),
            "agent ADD_TOKEN_TO_ALLOWED_LIST_ROLE"
        );
        assertTrue(
            registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, agent),
            "agent REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"
        );

        address self = address(registry);
        assertFalse(registry.hasRole(DEFAULT_ADMIN_ROLE, self), "registry DEFAULT_ADMIN_ROLE");
        assertFalse(
            registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, self),
            "registry ADD_TOKEN_TO_ALLOWED_LIST_ROLE"
        );
        assertFalse(
            registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, self),
            "registry REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"
        );

        address builder = address(allowedRecipientsBuilder);
        assertFalse(registry.hasRole(DEFAULT_ADMIN_ROLE, builder), "builder DEFAULT_ADMIN_ROLE");
        assertFalse(
            registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, builder),
            "builder ADD_TOKEN_TO_ALLOWED_LIST_ROLE"
        );
        assertFalse(
            registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, builder),
            "builder REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"
        );
    }
}
