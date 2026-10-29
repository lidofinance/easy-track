// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import {
    AllowedRecipientsBuilderSingleToken,
    IAllowedRecipientsFactory,
    IAllowedRecipientsRegistry,
    IAddAllowedRecipient,
    IEasyTrack,
    IRemoveAllowedRecipient,
    ITopUpAllowedRecipients
} from "contracts/payouts/single-token/AllowedRecipientsBuilderSingleToken.sol";
import {
    AllowedRecipientsFactorySingleToken
} from "contracts/payouts/single-token/AllowedRecipientsFactorySingleToken.sol";
import {EasyTrack} from "contracts/EasyTrack.sol";
import {EVMScriptExecutor} from "contracts/EVMScriptExecutor.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {Constants} from "test/foundry/unit/helpers/Constants.sol";
import {Roles} from "test/foundry/unit/helpers/Roles.sol";
import {
    BokkyPooBahsDateTimeContract
} from "test/foundry/unit/stubs/BokkyPooBahsDateTimeContract.sol";
import {CallsScriptStub} from "test/foundry/unit/stubs/CallsScriptStub.sol";
import {MiniMeTokenStub} from "test/foundry/unit/stubs/MiniMeTokenStub.sol";

contract AllowedRecipientsBuilderSingleTokenTest is Test {
    /// @dev Topic of the factory event the registry deployments are read back through, solc 0.8.6
    /// has no `Event.selector`
    bytes32 internal constant ALLOWED_RECIPIENTS_REGISTRY_DEPLOYED = keccak256(
        "AllowedRecipientsRegistryDeployed(address,address,address,address[],address[],address[],address[],address)"
    );

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
    address internal trustedCaller = makeAddr("trustedCaller");
    address internal recipient = makeAddr("recipient");
    address internal secondRecipient = makeAddr("secondRecipient");

    /// @dev python: accounts[4], an EOA the single factory deployments are wired to as a registry
    address internal recipientsRegistryStandIn = makeAddr("recipientsRegistryStandIn");

    MiniMeTokenStub internal ldo;
    EasyTrack internal easyTrack;
    EVMScriptExecutor internal evmScriptExecutor;
    BokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;
    AllowedRecipientsFactorySingleToken internal allowedRecipientsFactory;
    AllowedRecipientsBuilderSingleToken internal allowedRecipientsBuilder;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event TopUpAllowedRecipientsDeployed(
        address indexed creator,
        address indexed topUpAllowedRecipients,
        address trustedCaller,
        address allowedRecipientsRegistry,
        address finance,
        address token,
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
        allowedRecipientsFactory = new AllowedRecipientsFactorySingleToken();
        allowedRecipientsBuilder = new AllowedRecipientsBuilderSingleToken(
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
    function test_SetsInitialState() external view {
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
            finance,
            address(ldo),
            address(easyTrack)
        );

        vm.prank(stranger);
        ITopUpAllowedRecipients topUpAllowedRecipients =
            allowedRecipientsBuilder.deployTopUpAllowedRecipients(
                trustedCaller, recipientsRegistryStandIn, address(ldo)
            );

        assertEq(topUpAllowedRecipients.token(), address(ldo), "token");
        assertEq(
            topUpAllowedRecipients.allowedRecipientsRegistry(),
            recipientsRegistryStandIn,
            "allowedRecipientsRegistry"
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
        address[] memory recipients = Arrays.list(recipient, secondRecipient);

        vm.recordLogs();

        vm.prank(stranger);
        IAllowedRecipientsRegistry registry =
            allowedRecipientsBuilder.deployAllowedRecipientsRegistry(
                LIMIT, PERIOD_DURATION_MONTHS, recipients, _titles(), SPENT_AMOUNT, true
            );

        _assertRegistryDeployed(registry);
        _assertAllowedRecipients(registry, recipients, LIMIT, SPENT_AMOUNT);
        _assertRecipientsRegistryRoles(registry, true);
    }

    // python: test_deploy_recipients_registry_reverts_recipients_length
    function test_RevertWhen_RecipientsRegistryRecipientsLengthMismatch() external {
        vm.prank(stranger);
        vm.expectRevert("Recipients data length mismatch");
        allowedRecipientsBuilder.deployAllowedRecipientsRegistry(
            LIMIT,
            PERIOD_DURATION_MONTHS,
            Arrays.list(recipient, secondRecipient),
            Arrays.list(string("account 3")),
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
            Arrays.list(recipient, secondRecipient),
            _titles(),
            SPENT_AMOUNT,
            false
        );
    }

    // python: test_deploy_full_setup
    function test_DeploysFullSetup() external {
        address[] memory recipients = _fullSetupRecipients();

        vm.recordLogs();

        vm.prank(stranger);
        (
            IAllowedRecipientsRegistry registry,
            ITopUpAllowedRecipients topUpAllowedRecipients,
            IAddAllowedRecipient addAllowedRecipient,
            IRemoveAllowedRecipient removeAllowedRecipient
        ) = allowedRecipientsBuilder.deployFullSetup(
            FULL_SETUP_TRUSTED_CALLER,
            address(ldo),
            FULL_SETUP_LIMIT,
            PERIOD_DURATION_MONTHS,
            recipients,
            _fullSetupTitles(),
            FULL_SETUP_SPENT_AMOUNT
        );

        _assertRegistryDeployed(registry);
        assertEq(topUpAllowedRecipients.token(), address(ldo), "topUpAllowedRecipients.token");
        assertEq(
            topUpAllowedRecipients.allowedRecipientsRegistry(),
            address(registry),
            "topUpAllowedRecipients.allowedRecipientsRegistry"
        );
        assertEq(
            topUpAllowedRecipients.trustedCaller(),
            FULL_SETUP_TRUSTED_CALLER,
            "topUpAllowedRecipients.trustedCaller"
        );
        assertEq(
            addAllowedRecipient.allowedRecipientsRegistry(),
            address(registry),
            "addAllowedRecipient.allowedRecipientsRegistry"
        );
        assertEq(
            addAllowedRecipient.trustedCaller(),
            FULL_SETUP_TRUSTED_CALLER,
            "addAllowedRecipient.trustedCaller"
        );
        assertEq(
            removeAllowedRecipient.allowedRecipientsRegistry(),
            address(registry),
            "removeAllowedRecipient.allowedRecipientsRegistry"
        );
        assertEq(
            removeAllowedRecipient.trustedCaller(),
            FULL_SETUP_TRUSTED_CALLER,
            "removeAllowedRecipient.trustedCaller"
        );

        _assertAllowedRecipients(registry, recipients, FULL_SETUP_LIMIT, FULL_SETUP_SPENT_AMOUNT);
        _assertRecipientsRegistryRoles(registry, true);
    }

    // python: test_deploy_deploy_single_recipient_top_up_only_setup
    function test_DeploysSingleRecipientTopUpOnlySetup() external {
        vm.recordLogs();

        vm.prank(stranger);
        (IAllowedRecipientsRegistry registry, ITopUpAllowedRecipients topUpAllowedRecipients) = allowedRecipientsBuilder.deploySingleRecipientTopUpOnlySetup(
            recipient, "recipient", address(ldo), LIMIT, PERIOD_DURATION_MONTHS, SPENT_AMOUNT
        );

        _assertRegistryDeployed(registry);
        assertEq(
            topUpAllowedRecipients.allowedRecipientsRegistry(),
            address(registry),
            "allowedRecipientsRegistry"
        );
        assertEq(topUpAllowedRecipients.token(), address(ldo), "token");

        _assertAllowedRecipients(registry, Arrays.list(recipient), LIMIT, SPENT_AMOUNT);
        _assertRecipientsRegistryRoles(registry, false);
    }

    /// @dev The address of the factory's next `new`, so `expectEmit` can pin the deployed topic
    function _nextFactoryDeployment() private view returns (address) {
        return vm.computeCreateAddress(
            address(allowedRecipientsFactory), vm.getNonce(address(allowedRecipientsFactory))
        );
    }

    /// @dev python: tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"].
    /// The factory announced the `registry` the builder returned
    function _assertRegistryDeployed(IAllowedRecipientsRegistry registry) private {
        assertEq(
            _deployedAddress(vm.getRecordedLogs(), ALLOWED_RECIPIENTS_REGISTRY_DEPLOYED),
            address(registry),
            "AllowedRecipientsRegistryDeployed.allowedRecipientsRegistry"
        );
    }

    /// @dev The deployed address the factory emitted under `eventTopic`
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

    /// @dev python: ["account 3", "account 4"]
    function _titles() private pure returns (string[] memory) {
        return Arrays.list(string("account 3"), string("account 4"));
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
            registry.hasRole(Roles.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, agent),
            "agent ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE"
        );
        assertTrue(
            registry.hasRole(Roles.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, agent),
            "agent REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE"
        );
        assertTrue(registry.hasRole(Roles.SET_PARAMETERS_ROLE, agent), "agent SET_PARAMETERS_ROLE");
        assertTrue(
            registry.hasRole(Roles.UPDATE_SPENT_AMOUNT_ROLE, agent),
            "agent UPDATE_SPENT_AMOUNT_ROLE"
        );
        assertTrue(registry.hasRole(Roles.DEFAULT_ADMIN_ROLE, agent), "agent DEFAULT_ADMIN_ROLE");

        address executor = address(evmScriptExecutor);
        assertEq(
            registry.hasRole(Roles.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, executor),
            grantedToEVMScriptExecutor,
            "evmScriptExecutor ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE"
        );
        assertEq(
            registry.hasRole(Roles.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, executor),
            grantedToEVMScriptExecutor,
            "evmScriptExecutor REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE"
        );
        assertTrue(
            registry.hasRole(Roles.UPDATE_SPENT_AMOUNT_ROLE, executor),
            "evmScriptExecutor UPDATE_SPENT_AMOUNT_ROLE"
        );
        assertFalse(
            registry.hasRole(Roles.SET_PARAMETERS_ROLE, executor),
            "evmScriptExecutor SET_PARAMETERS_ROLE"
        );
        assertFalse(
            registry.hasRole(Roles.DEFAULT_ADMIN_ROLE, executor),
            "evmScriptExecutor DEFAULT_ADMIN_ROLE"
        );

        address self = address(registry);
        assertFalse(
            registry.hasRole(Roles.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, self),
            "registry ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE"
        );
        assertFalse(
            registry.hasRole(Roles.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, self),
            "registry REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE"
        );
        assertFalse(
            registry.hasRole(Roles.SET_PARAMETERS_ROLE, self), "registry SET_PARAMETERS_ROLE"
        );
        assertFalse(
            registry.hasRole(Roles.UPDATE_SPENT_AMOUNT_ROLE, self),
            "registry UPDATE_SPENT_AMOUNT_ROLE"
        );
        assertFalse(registry.hasRole(Roles.DEFAULT_ADMIN_ROLE, self), "registry DEFAULT_ADMIN_ROLE");
    }
}
