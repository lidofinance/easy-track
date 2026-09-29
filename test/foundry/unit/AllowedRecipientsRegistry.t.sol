// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AllowedRecipientsRegistry} from "contracts/AllowedRecipientsRegistry.sol";
import {LimitsChecker} from "contracts/LimitsChecker.sol";
import {
    IBokkyPooBahsDateTimeContract
} from "contracts/interfaces/IBokkyPooBahsDateTimeContract.sol";
import {
    LimitsCheckerWithPrivateViewsExposed
} from "contracts/test/LimitsCheckerWithPrivateViewsExposed.sol.sol";
import {
    BokkyPooBahsDateTimeContract
} from "test/foundry/unit/stubs/BokkyPooBahsDateTimeContract.sol";
import {Calendar} from "test/foundry/unit/helpers/Calendar.sol";
import {TestHelpers} from "test/foundry/unit/helpers/TestHelpers.sol";

contract AllowedRecipientsRegistryTest is Test {
    string internal constant RECIPIENT_TITLE = "New Allowed Recipient";

    bytes32 internal constant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE");
    bytes32 internal constant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE");
    bytes32 internal constant SET_PARAMETERS_ROLE = keccak256("SET_PARAMETERS_ROLE");
    bytes32 internal constant UPDATE_SPENT_AMOUNT_ROLE = keccak256("UPDATE_SPENT_AMOUNT_ROLE");

    address internal owner = makeAddr("owner");
    address internal voting = makeAddr("voting");
    address internal stranger = makeAddr("stranger");
    address internal addRecipientRoleHolder = makeAddr("addRecipientRoleHolder");
    address internal removeRecipientRoleHolder = makeAddr("removeRecipientRoleHolder");
    address internal setParametersRoleHolder = makeAddr("setParametersRoleHolder");
    address internal updateSpentAmountRoleHolder = makeAddr("updateSpentAmountRoleHolder");
    address internal recipient1 = makeAddr("recipient1");
    address internal recipient2 = makeAddr("recipient2");

    BokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;
    AllowedRecipientsRegistry internal allowedRecipientsRegistry;

    function setUp() public {
        bokkyPooBahsDateTimeContract = new BokkyPooBahsDateTimeContract();

        vm.prank(owner);
        allowedRecipientsRegistry = new AllowedRecipientsRegistry(
            owner,
            _addresses(addRecipientRoleHolder),
            _addresses(removeRecipientRoleHolder),
            _addresses(setParametersRoleHolder),
            _addresses(updateSpentAmountRoleHolder),
            bokkyPooBahsDateTimeContract
        );

        vm.label(address(bokkyPooBahsDateTimeContract), "BokkyPooBahsDateTimeContract");
        vm.label(address(allowedRecipientsRegistry), "AllowedRecipientsRegistry");
    }

    // python: test_registry_initial_state
    function test_RegistryInitialState() external view {
        assertTrue(
            allowedRecipientsRegistry.hasRole(
                ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, addRecipientRoleHolder
            ),
            "addRecipientRoleHolder role"
        );
        assertTrue(
            allowedRecipientsRegistry.hasRole(
                REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, removeRecipientRoleHolder
            ),
            "removeRecipientRoleHolder role"
        );
        assertTrue(
            allowedRecipientsRegistry.hasRole(SET_PARAMETERS_ROLE, setParametersRoleHolder),
            "setParametersRoleHolder role"
        );
        assertTrue(
            allowedRecipientsRegistry.hasRole(
                UPDATE_SPENT_AMOUNT_ROLE, updateSpentAmountRoleHolder
            ),
            "updateSpentAmountRoleHolder role"
        );
        assertTrue(
            allowedRecipientsRegistry.hasRole(
                allowedRecipientsRegistry.DEFAULT_ADMIN_ROLE(), owner
            ),
            "owner admin role"
        );
        assertEq(
            address(allowedRecipientsRegistry.bokkyPooBahsDateTimeContract()),
            address(bokkyPooBahsDateTimeContract),
            "bokkyPooBahsDateTimeContract"
        );

        address[4] memory roleHolders = [
            addRecipientRoleHolder,
            removeRecipientRoleHolder,
            setParametersRoleHolder,
            updateSpentAmountRoleHolder
        ];
        for (uint256 i; i < roleHolders.length; ++i) {
            assertFalse(
                allowedRecipientsRegistry.hasRole(
                    allowedRecipientsRegistry.DEFAULT_ADMIN_ROLE(), roleHolders[i]
                ),
                "role holder admin role"
            );
        }

        assertEq(allowedRecipientsRegistry.spendableBalance(), 0, "spendableBalance");

        (uint256 limit, uint256 periodDurationMonths) =
            allowedRecipientsRegistry.getLimitParameters();
        assertEq(limit, 0, "limit");
        assertEq(periodDurationMonths, 0, "periodDurationMonths");
        assertEq(allowedRecipientsRegistry.getAllowedRecipients().length, 0, "allowedRecipients");
    }

    // python: test_registry_zero_admin_allowed
    function test_RegistryZeroAdminAllowed() external {
        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            address(0),
            _addresses(owner),
            _addresses(owner),
            _addresses(owner),
            _addresses(owner),
            bokkyPooBahsDateTimeContract
        );

        assertTrue(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), address(0)), "zero admin role");
    }

    // python: test_registry_none_role_holders_allowed
    function test_RegistryNoneRoleHoldersAllowed() external {
        address[] memory noHolders = new address[](0);

        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            owner, noHolders, noHolders, noHolders, noHolders, bokkyPooBahsDateTimeContract
        );

        assertTrue(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), owner), "owner admin role");
    }

    // python: test_registry_zero_booky_poo_bahs_data_time_address_allowed
    function test_RegistryZeroBokkyPooBahsDateTimeAddressAllowed() external {
        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            owner,
            _addresses(owner),
            _addresses(owner),
            _addresses(owner),
            _addresses(owner),
            IBokkyPooBahsDateTimeContract(address(0))
        );

        assertEq(
            address(registry.bokkyPooBahsDateTimeContract()),
            address(0),
            "bokkyPooBahsDateTimeContract"
        );
    }

    // python: test_rights_are_not_shared_by_different_roles
    function test_RightsAreNotSharedByDifferentRoles() external {
        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            voting,
            _addresses(addRecipientRoleHolder),
            _addresses(removeRecipientRoleHolder),
            _addresses(setParametersRoleHolder),
            _addresses(updateSpentAmountRoleHolder),
            bokkyPooBahsDateTimeContract
        );

        assertTrue(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), voting), "voting admin role");

        address[5] memory callers = [
            owner,
            removeRecipientRoleHolder,
            setParametersRoleHolder,
            updateSpentAmountRoleHolder,
            stranger
        ];
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(callers[i], ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE)
            );
            registry.addRecipient(recipient1, RECIPIENT_TITLE);
        }

        callers = [
            owner,
            addRecipientRoleHolder,
            setParametersRoleHolder,
            updateSpentAmountRoleHolder,
            stranger
        ];
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(callers[i], REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE)
            );
            registry.removeRecipient(recipient1);
        }

        callers = [
            owner,
            addRecipientRoleHolder,
            removeRecipientRoleHolder,
            updateSpentAmountRoleHolder,
            stranger
        ];
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], SET_PARAMETERS_ROLE));
            registry.setLimitParameters(0, 1);

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], SET_PARAMETERS_ROLE));
            registry.setBokkyPooBahsDateTimeContract(address(0));

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], SET_PARAMETERS_ROLE));
            registry.unsafeSetSpentAmount(0);
        }

        callers = [
            owner,
            addRecipientRoleHolder,
            removeRecipientRoleHolder,
            setParametersRoleHolder,
            stranger
        ];
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], UPDATE_SPENT_AMOUNT_ROLE));
            registry.updateSpentAmount(1);
        }
    }

    // python: test_multiple_role_holders
    function test_MultipleRoleHolders() external {
        address[20] memory accounts = _sweepAccounts();
        address[] memory addRecipientRoleHolders = _addresses(accounts[2], accounts[3]);
        address[] memory removeRecipientRoleHolders = _addresses(accounts[4], accounts[5]);
        address[] memory setParametersRoleHolders = _addresses(accounts[6], accounts[7]);
        address[] memory updateSpentAmountRoleHolders = _addresses(accounts[8], accounts[9]);

        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            voting,
            addRecipientRoleHolders,
            removeRecipientRoleHolders,
            setParametersRoleHolders,
            updateSpentAmountRoleHolders,
            bokkyPooBahsDateTimeContract
        );

        address[] memory callers = _callersWithout(accounts, addRecipientRoleHolders);
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(callers[i], ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE)
            );
            registry.addRecipient(callers[i], RECIPIENT_TITLE);
        }

        // python: accounts[0:5] added by the first holder, accounts[5:10] by the second
        for (uint256 i; i < 5; ++i) {
            vm.prank(addRecipientRoleHolders[0]);
            registry.addRecipient(accounts[i], RECIPIENT_TITLE);
        }

        for (uint256 i = 5; i < 10; ++i) {
            vm.prank(addRecipientRoleHolders[1]);
            registry.addRecipient(accounts[i], RECIPIENT_TITLE);
        }

        callers = _callersWithout(accounts, removeRecipientRoleHolders);
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(callers[i], REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE)
            );
            registry.removeRecipient(callers[i]);
        }

        vm.prank(removeRecipientRoleHolders[0]);
        registry.removeRecipient(removeRecipientRoleHolders[0]);

        vm.prank(removeRecipientRoleHolders[1]);
        registry.removeRecipient(removeRecipientRoleHolders[1]);

        callers = _callersWithout(accounts, setParametersRoleHolders);
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], SET_PARAMETERS_ROLE));
            registry.setLimitParameters(5, 1);

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], SET_PARAMETERS_ROLE));
            registry.setBokkyPooBahsDateTimeContract(address(0));

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], SET_PARAMETERS_ROLE));
            registry.unsafeSetSpentAmount(0);
        }

        vm.prank(setParametersRoleHolders[0]);
        registry.setLimitParameters(5, 1);

        vm.prank(setParametersRoleHolders[1]);
        registry.setLimitParameters(5, 1);

        callers = _callersWithout(accounts, updateSpentAmountRoleHolders);
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], UPDATE_SPENT_AMOUNT_ROLE));
            registry.updateSpentAmount(1);
        }

        vm.prank(updateSpentAmountRoleHolders[0]);
        registry.updateSpentAmount(1);

        vm.prank(updateSpentAmountRoleHolders[1]);
        registry.updateSpentAmount(1);
    }

    // python: test_add_recipient
    function test_AddRecipient() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipient1), "isRecipientAllowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            _addresses(recipient1),
            "allowedRecipients"
        );
    }

    // python: test_add_recipient_with_empty_title
    function test_AddRecipientWithEmptyTitle() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, "");

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipient1), "isRecipientAllowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            _addresses(recipient1),
            "allowedRecipients"
        );
    }

    // python: test_add_recipient_with_zero_address
    function test_AddRecipientWithZeroAddress() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(address(0), RECIPIENT_TITLE);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(address(0)), "isRecipientAllowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            _addresses(address(0)),
            "allowedRecipients"
        );
    }

    // python: test_add_multiple_recipients
    function test_AddMultipleRecipients() external {
        vm.startPrank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);
        allowedRecipientsRegistry.addRecipient(recipient2, RECIPIENT_TITLE);
        vm.stopPrank();

        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipient1),
            "isRecipientAllowed recipient1"
        );
        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipient2),
            "isRecipientAllowed recipient2"
        );
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            _addresses(recipient1, recipient2),
            "allowedRecipients"
        );
    }

    // python: test_fail_if_add_the_same_recipient
    function test_RevertWhen_AddingTheSameRecipient() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipient1), "isRecipientAllowed");

        vm.prank(addRecipientRoleHolder);
        vm.expectRevert("RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST");
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);

        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients().length, 1, "allowedRecipients length"
        );
    }

    // python: test_remove_recipient
    function test_RemoveRecipient() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipient1), "isRecipientAllowed");

        vm.prank(removeRecipientRoleHolder);
        allowedRecipientsRegistry.removeRecipient(recipient1);

        assertFalse(
            allowedRecipientsRegistry.isRecipientAllowed(recipient1),
            "isRecipientAllowed after removal"
        );
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients().length, 0, "allowedRecipients length"
        );
    }

    // python: test_remove_not_last_recipient_in_the_list
    function test_RemoveNotLastRecipientInTheList() external {
        vm.startPrank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);
        allowedRecipientsRegistry.addRecipient(recipient2, RECIPIENT_TITLE);
        vm.stopPrank();

        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipient1),
            "isRecipientAllowed recipient1"
        );
        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipient2),
            "isRecipientAllowed recipient2"
        );

        vm.prank(removeRecipientRoleHolder);
        allowedRecipientsRegistry.removeRecipient(recipient1);

        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            _addresses(recipient2),
            "allowedRecipients"
        );
    }

    // python: test_fail_if_remove_recipient_from_empty_allowed_list
    function test_RevertWhen_RemovingRecipientFromEmptyAllowedList() external {
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients().length, 0, "allowedRecipients length"
        );
        assertFalse(allowedRecipientsRegistry.isRecipientAllowed(recipient1), "isRecipientAllowed");

        vm.prank(removeRecipientRoleHolder);
        vm.expectRevert("RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST");
        allowedRecipientsRegistry.removeRecipient(recipient1);

        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients().length,
            0,
            "allowedRecipients length after the revert"
        );
    }

    // python: test_fail_if_remove_not_allowed_recipient
    function test_RevertWhen_RemovingNotAllowedRecipient() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);

        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipient1),
            "isRecipientAllowed recipient1"
        );

        vm.prank(removeRecipientRoleHolder);
        vm.expectRevert("RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST");
        allowedRecipientsRegistry.removeRecipient(recipient2);

        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            _addresses(recipient1),
            "allowedRecipients"
        );
        assertTrue(
            allowedRecipientsRegistry.isRecipientAllowed(recipient1),
            "isRecipientAllowed recipient1 after the revert"
        );
        assertFalse(
            allowedRecipientsRegistry.isRecipientAllowed(recipient2),
            "isRecipientAllowed recipient2"
        );
    }

    /// @dev python: accounts[0:20]. The eight role holders of the sweep sit at their Python indices
    function _sweepAccounts() private returns (address[20] memory accounts) {
        accounts[0] = owner;
        accounts[1] = makeAddr("account1");
        accounts[2] = makeAddr("addRecipientRoleHolder1");
        accounts[3] = makeAddr("addRecipientRoleHolder2");
        accounts[4] = makeAddr("removeRecipientRoleHolder1");
        accounts[5] = makeAddr("removeRecipientRoleHolder2");
        accounts[6] = makeAddr("setParametersRoleHolder1");
        accounts[7] = makeAddr("setParametersRoleHolder2");
        accounts[8] = makeAddr("updateSpentAmountRoleHolder1");
        accounts[9] = makeAddr("updateSpentAmountRoleHolder2");

        for (uint256 i = 10; i < accounts.length; ++i) {
            accounts[i] = makeAddr(string(abi.encodePacked("account", vm.toString(i))));
        }
    }

    /// @dev The sweep accounts that are neither of the two `roleHolders`
    function _callersWithout(address[20] memory accounts, address[] memory roleHolders)
        private
        pure
        returns (address[] memory callers)
    {
        callers = new address[](accounts.length - roleHolders.length);
        uint256 count;

        for (uint256 i; i < accounts.length; ++i) {
            if (accounts[i] == roleHolders[0] || accounts[i] == roleHolders[1]) {
                continue;
            }
            callers[count++] = accounts[i];
        }
    }

    function _addresses(address account) private pure returns (address[] memory addresses) {
        addresses = new address[](1);
        addresses[0] = account;
    }

    function _addresses(address account1, address account2)
        private
        pure
        returns (address[] memory addresses)
    {
        addresses = new address[](2);
        addresses[0] = account1;
        addresses[1] = account2;
    }
}

contract LimitsCheckerTest is Test {
    uint256 internal constant MAX_SECONDS_IN_MONTH = 31 days;
    uint256 internal constant PERIOD_LIMIT = 3 ether;
    uint256 internal constant PERIOD_DURATION = 1;
    uint256 internal constant INITIAL_LIMIT = 100 ether;
    uint256 internal constant INITIAL_PERIOD_DURATION = 3;

    bytes32 internal constant SET_PARAMETERS_ROLE = keccak256("SET_PARAMETERS_ROLE");
    bytes32 internal constant UPDATE_SPENT_AMOUNT_ROLE = keccak256("UPDATE_SPENT_AMOUNT_ROLE");

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal setParametersRoleHolder = makeAddr("setParametersRoleHolder");
    address internal updateSpentAmountRoleHolder = makeAddr("updateSpentAmountRoleHolder");

    BokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;
    LimitsChecker internal limitsChecker;
    LimitsCheckerWithPrivateViewsExposed internal limitsCheckerWithPrivateViewsExposed;

    // Copied from LimitsChecker so the test can `emit` them for `vm.expectEmit`
    event LimitsParametersChanged(uint256 _limit, uint256 _periodDurationMonths);
    event SpendableAmountChanged(
        uint256 _alreadySpentAmount,
        uint256 _spendableBalance,
        uint256 indexed _periodStartTimestamp,
        uint256 _periodEndTimestamp
    );
    event CurrentPeriodAdvanced(uint256 indexed _periodStartTimestamp);
    event BokkyPooBahsDateTimeContractChanged(address indexed _newAddress);
    event SpentAmountChanged(uint256 _newSpentAmount);

    function setUp() public {
        bokkyPooBahsDateTimeContract = new BokkyPooBahsDateTimeContract();

        vm.startPrank(owner);
        limitsChecker = new LimitsChecker(
            _addresses(setParametersRoleHolder),
            _addresses(updateSpentAmountRoleHolder),
            bokkyPooBahsDateTimeContract
        );
        limitsCheckerWithPrivateViewsExposed = new LimitsCheckerWithPrivateViewsExposed(
            _addresses(setParametersRoleHolder),
            _addresses(updateSpentAmountRoleHolder),
            bokkyPooBahsDateTimeContract
        );
        vm.stopPrank();

        vm.label(address(bokkyPooBahsDateTimeContract), "BokkyPooBahsDateTimeContract");
        vm.label(address(limitsChecker), "LimitsChecker");
        vm.label(
            address(limitsCheckerWithPrivateViewsExposed), "LimitsCheckerWithPrivateViewsExposed"
        );
    }

    // python: test_access_stranger_cannot_set_limit_parameters
    function test_RevertWhen_StrangerSetsLimitParameters() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, SET_PARAMETERS_ROLE));
        limitsChecker.setLimitParameters(123, 1);
    }

    // python: test_access_stranger_cannot_set_date_time_library, the shadowed definition at L259
    function test_RevertWhen_StrangerSetsBokkyPooBahsDateTimeContract() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, SET_PARAMETERS_ROLE));
        limitsChecker.setBokkyPooBahsDateTimeContract(address(0));
    }

    // python: test_access_stranger_cannot_set_date_time_library, the collected definition at L266
    function test_RevertWhen_StrangerUnsafeSetsSpentAmount() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, SET_PARAMETERS_ROLE));
        limitsChecker.unsafeSetSpentAmount(0);
    }

    // python: test_access_stranger_cannot_update_spent_amount
    function test_RevertWhen_StrangerUpdatesSpentAmount() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, UPDATE_SPENT_AMOUNT_ROLE));
        limitsChecker.updateSpentAmount(123);
    }

    // python: test_set_date_time_contract
    function test_SetDateTimeContract() external {
        address newAddress = makeAddr("newBokkyPooBahsDateTimeContract");
        assertNotEq(
            address(limitsChecker.bokkyPooBahsDateTimeContract()),
            newAddress,
            "bokkyPooBahsDateTimeContract before"
        );

        vm.expectEmit(address(limitsChecker));
        emit BokkyPooBahsDateTimeContractChanged(newAddress);

        vm.recordLogs();

        vm.prank(setParametersRoleHolder);
        limitsChecker.setBokkyPooBahsDateTimeContract(newAddress);

        assertEq(
            address(limitsChecker.bokkyPooBahsDateTimeContract()),
            newAddress,
            "bokkyPooBahsDateTimeContract"
        );
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_fail_if_set_same_time_contract
    function test_RevertWhen_SettingTheSameDateTimeContract() external {
        address currentAddress = address(limitsChecker.bokkyPooBahsDateTimeContract());

        vm.prank(setParametersRoleHolder);
        vm.expectRevert("SAME_DATE_TIME_CONTRACT_ADDRESS");
        limitsChecker.setBokkyPooBahsDateTimeContract(currentAddress);
    }

    // python: test_unsafe_set_spent_amount_when_spent_amount_exceeds_limit
    function test_RevertWhen_UnsafeSetSpentAmountExceedsLimit() external {
        _givenLimitParametersSet(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);

        _assertLimitParameters(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);
        (uint256 alreadySpentAmount,,,) = limitsChecker.getPeriodState();
        assertEq(alreadySpentAmount, 0, "_alreadySpentAmount");

        vm.prank(setParametersRoleHolder);
        vm.expectRevert("ERROR_SPENT_AMOUNT_EXCEEDS_LIMIT");
        limitsChecker.unsafeSetSpentAmount(INITIAL_LIMIT + 1);
    }

    // python: test_unsafe_set_spent_amount_when_new_spent_amount_the_same
    function test_UnsafeSetSpentAmountWhenNewSpentAmountIsTheSame() external {
        _givenLimitParametersSet(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);

        _assertLimitParameters(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);
        (uint256 alreadySpentAmount,,,) = limitsChecker.getPeriodState();
        assertEq(alreadySpentAmount, 0, "_alreadySpentAmount");

        vm.recordLogs();

        vm.prank(setParametersRoleHolder);
        limitsChecker.unsafeSetSpentAmount(alreadySpentAmount);

        (uint256 alreadySpentAmountAfter,,,) = limitsChecker.getPeriodState();
        assertEq(alreadySpentAmountAfter, alreadySpentAmount, "_alreadySpentAmount after");
        // unsafeSetSpentAmount emits nothing but SpentAmountChanged, so no log means no event
        assertEq(vm.getRecordedLogs().length, 0, "events");
    }

    // python: test_unsafe_set_spent_amount
    function test_UnsafeSetSpentAmount() external {
        _givenLimitParametersSet(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);

        _assertLimitParameters(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);
        (uint256 alreadySpentAmount,,,) = limitsChecker.getPeriodState();
        assertEq(alreadySpentAmount, 0, "_alreadySpentAmount");

        vm.expectEmit(address(limitsChecker));
        emit SpentAmountChanged(INITIAL_LIMIT / 2);

        vm.prank(setParametersRoleHolder);
        limitsChecker.unsafeSetSpentAmount(INITIAL_LIMIT / 2);

        (alreadySpentAmount,,,) = limitsChecker.getPeriodState();
        assertEq(alreadySpentAmount, INITIAL_LIMIT / 2, "_alreadySpentAmount at half the limit");

        vm.expectEmit(address(limitsChecker));
        emit SpentAmountChanged(INITIAL_LIMIT);

        vm.prank(setParametersRoleHolder);
        limitsChecker.unsafeSetSpentAmount(INITIAL_LIMIT);

        (alreadySpentAmount,,,) = limitsChecker.getPeriodState();
        assertEq(alreadySpentAmount, INITIAL_LIMIT, "_alreadySpentAmount at the limit");
    }

    // python: test_set_limit_parameters_happy_path
    function test_SetLimitParametersHappyPath() external {
        (uint256 periodStart,) = TestHelpers.calcPeriodRange(PERIOD_DURATION, block.timestamp);

        vm.expectEmit(address(limitsChecker));
        emit CurrentPeriodAdvanced(periodStart);

        vm.expectEmit(address(limitsChecker));
        emit LimitsParametersChanged(PERIOD_LIMIT, PERIOD_DURATION);

        vm.recordLogs();

        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

        assertEq(vm.getRecordedLogs().length, 2, "events");

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        _assertLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);
        assertTrue(
            limitsChecker.isUnderSpendableBalance(PERIOD_LIMIT, 0), "isUnderSpendableBalance"
        );
    }

    // python: test_period_range_calculation_for_all_allowed_period_durations
    function test_PeriodRangeCalculationForAllAllowedPeriodDurations() external {
        (, uint256 periodDurationMonths) = limitsCheckerWithPrivateViewsExposed.getLimitParameters();
        assertEq(periodDurationMonths, 0, "periodDurationMonths");

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(1);

        uint256[5] memory periodDurations = [uint256(1), 2, 3, 6, 12];
        // 24 half-month steps cover two years of period boundaries
        for (uint256 step; step < 24; ++step) {
            for (uint256 i; i < periodDurations.length; ++i) {
                vm.prank(setParametersRoleHolder);
                limitsCheckerWithPrivateViewsExposed.setLimitParameters(0, periodDurations[i]);

                (,, uint256 periodStart, uint256 periodEnd) =
                    limitsCheckerWithPrivateViewsExposed.getPeriodState();
                (uint256 expectedPeriodStart, uint256 expectedPeriodEnd) =
                    TestHelpers.calcPeriodRange(periodDurations[i], block.timestamp);

                assertEq(periodStart, expectedPeriodStart, "_periodStartTimestamp");
                assertEq(periodEnd, expectedPeriodEnd, "_periodEndTimestamp");
            }

            skip(MAX_SECONDS_IN_MONTH / 2);
        }
    }

    // python: test_fail_if_set_incorrect_period_durations[0]
    function test_RevertWhen_PeriodDurationIs0() external {
        _assertRevertOnPeriodDuration(0);
    }

    // python: test_fail_if_set_incorrect_period_durations[4]
    function test_RevertWhen_PeriodDurationIs4() external {
        _assertRevertOnPeriodDuration(4);
    }

    // python: test_fail_if_set_incorrect_period_durations[5]
    function test_RevertWhen_PeriodDurationIs5() external {
        _assertRevertOnPeriodDuration(5);
    }

    // python: test_fail_if_set_incorrect_period_durations[7]
    function test_RevertWhen_PeriodDurationIs7() external {
        _assertRevertOnPeriodDuration(7);
    }

    // python: test_fail_if_set_incorrect_period_durations[8]
    function test_RevertWhen_PeriodDurationIs8() external {
        _assertRevertOnPeriodDuration(8);
    }

    // python: test_fail_if_set_incorrect_period_durations[9]
    function test_RevertWhen_PeriodDurationIs9() external {
        _assertRevertOnPeriodDuration(9);
    }

    // python: test_fail_if_set_incorrect_period_durations[10]
    function test_RevertWhen_PeriodDurationIs10() external {
        _assertRevertOnPeriodDuration(10);
    }

    // python: test_fail_if_set_incorrect_period_durations[11]
    function test_RevertWhen_PeriodDurationIs11() external {
        _assertRevertOnPeriodDuration(11);
    }

    // python: test_fail_if_set_incorrect_period_durations[13]
    function test_RevertWhen_PeriodDurationIs13() external {
        _assertRevertOnPeriodDuration(13);
    }

    // python: test_fail_if_set_incorrect_period_durations[14]
    function test_RevertWhen_PeriodDurationIs14() external {
        _assertRevertOnPeriodDuration(14);
    }

    // python: test_fail_if_set_incorrect_period_durations[100500]
    function test_RevertWhen_PeriodDurationIs100500() external {
        _assertRevertOnPeriodDuration(100500);
    }

    // python: test_get_first_month_in_period_for_all_allowed_period_durations[1-1-1] to [1-12-12]
    function test_GetFirstMonthInPeriodForPeriodDuration1() external {
        _assertFirstMonthInPeriodForEveryMonth(1);
    }

    // python: test_get_first_month_in_period_for_all_allowed_period_durations[2-1-1] to [2-12-11]
    function test_GetFirstMonthInPeriodForPeriodDuration2() external {
        _assertFirstMonthInPeriodForEveryMonth(2);
    }

    // python: test_get_first_month_in_period_for_all_allowed_period_durations[3-1-1] to [3-12-10]
    function test_GetFirstMonthInPeriodForPeriodDuration3() external {
        _assertFirstMonthInPeriodForEveryMonth(3);
    }

    // python: test_get_first_month_in_period_for_all_allowed_period_durations[6-1-1] to [6-12-7]
    function test_GetFirstMonthInPeriodForPeriodDuration6() external {
        _assertFirstMonthInPeriodForEveryMonth(6);
    }

    // python: test_get_first_month_in_period_for_all_allowed_period_durations[12-1-1] to [12-12-1]
    function test_GetFirstMonthInPeriodForPeriodDuration12() external {
        _assertFirstMonthInPeriodForEveryMonth(12);
    }

    // python: test_fail_if_set_limit_greater_than_max_limit
    function test_RevertWhen_LimitIsGreaterThanMaxLimit() external {
        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(2 ** 128 - 1, PERIOD_DURATION);

        vm.prank(setParametersRoleHolder);
        vm.expectRevert("TOO_LARGE_LIMIT");
        limitsChecker.setLimitParameters(2 ** 128, PERIOD_DURATION);
    }

    // python: test_limits_checker_views_in_next_period
    function test_LimitsCheckerViewsInNextPeriod() external {
        uint256 periodLimit = 10 ether;
        uint256 payoutAmount = 3 ether;
        uint256 spendableBalance = 7 ether;
        _givenLimitParametersSet(periodLimit, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(payoutAmount);

        assertEq(limitsChecker.spendableBalance(), spendableBalance, "spendableBalance");
        _assertPeriodSpending(payoutAmount, spendableBalance);

        skip(MAX_SECONDS_IN_MONTH);

        // the views still report the old period: only a call that shifts the period advances it
        assertEq(
            limitsChecker.spendableBalance(),
            spendableBalance,
            "spendableBalance in the next period"
        );
        _assertPeriodSpending(payoutAmount, spendableBalance);
    }

    // python: test_update_spent_amount_within_the_limit
    function test_UpdateSpentAmountWithinTheLimit() external {
        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        uint256 periodStart = TestHelpers.getMonthStartTimestamp(block.timestamp);
        uint256 periodEnd = TestHelpers.getMonthStartTimestamp(
            TestHelpers.getDateInNextPeriod(block.timestamp, PERIOD_DURATION)
        );
        uint256 spending = 2 ether;
        uint256 spendable = 1 ether;
        _givenLimitParametersSet(PERIOD_LIMIT, PERIOD_DURATION);

        vm.expectEmit(address(limitsChecker));
        emit SpendableAmountChanged(spending, spendable, periodStart, periodEnd);

        vm.recordLogs();

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertTrue(limitsChecker.isUnderSpendableBalance(spendable, 0), "isUnderSpendableBalance");
        // a motion lasting a month enacts in the next period, where the whole limit is spendable
        assertTrue(
            limitsChecker.isUnderSpendableBalance(PERIOD_LIMIT, MAX_SECONDS_IN_MONTH),
            "isUnderSpendableBalance in the next period"
        );
        assertEq(vm.getRecordedLogs().length, 1, "events");
    }

    // python: test_update_spent_amount_precisely_to_the_limit_in_multiple_portions
    function test_UpdateSpentAmountPreciselyToTheLimitInMultiplePortions() external {
        uint256 spending = 1 ether;
        uint256 spendable = 2 ether;
        _givenLimitParametersSet(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), spendable, "spendableBalance");
        _assertPeriodSpending(spending, spendable);
        assertTrue(limitsChecker.isUnderSpendableBalance(spendable, 0), "isUnderSpendableBalance");
        assertTrue(
            limitsChecker.isUnderSpendableBalance(PERIOD_LIMIT, MAX_SECONDS_IN_MONTH),
            "isUnderSpendableBalance in the next period"
        );

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        _assertPeriodSpending(2 ether, 1 ether);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        _assertPeriodSpending(3 ether, 0);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);
    }

    // python: test_spending_amount_is_restored_in_the_next_period
    function test_SpendingAmountIsRestoredInTheNextPeriod() external {
        uint256 spending = 3 ether;
        _givenLimitParametersSet(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), 0, "spendableBalance");

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(spending);

        skip(MAX_SECONDS_IN_MONTH);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), 0, "spendableBalance in the next period");
    }

    // python: test_fail_if_update_spent_amount_beyond_the_limit
    function test_RevertWhen_UpdatingSpentAmountBeyondTheLimit() external {
        _givenLimitParametersSet(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        (, uint256 spendableBalance,,) = limitsChecker.getPeriodState();
        assertEq(spendableBalance, PERIOD_LIMIT, "_spendableBalanceInPeriod");

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(PERIOD_LIMIT + 1);
    }

    // python: test_spendable_amount_increased_if_limit_increased
    function test_SpendableAmountIncreasedIfLimitIncreased() external {
        uint256 spending = 3 ether;
        uint256 newPeriodLimit = 6 ether;
        uint256 newSpendable = 3 ether;
        _givenLimitParametersSet(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), 0, "spendableBalance");
        _assertPeriodSpending(spending, 0);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);

        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(newPeriodLimit, PERIOD_DURATION);

        // the spent amount stays as it was and the raise is spendable
        _assertPeriodSpending(spending, newSpendable);
        assertEq(limitsChecker.spendableBalance(), newSpendable, "spendableBalance after the raise");

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(newSpendable);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);
    }

    // python: test_spendable_amount_if_limit_decreased_below_spent_amount
    function test_SpendableAmountIfLimitDecreasedBelowSpentAmount() external {
        uint256 spending = 1 ether;
        uint256 spendable = 2 ether;
        uint256 newPeriodLimit = 1 ether - 1;
        _givenLimitParametersSet(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), spendable, "spendableBalance");
        _assertPeriodSpending(spending, spendable);

        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(newPeriodLimit, PERIOD_DURATION);

        // the spent amount stays as it was and the spendable balance clamps at zero
        _assertPeriodSpending(spending, 0);
        assertEq(limitsChecker.spendableBalance(), 0, "spendableBalance after the cut");

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);
    }

    // python: test_spendable_amount_if_limit_decreased_not_below_spent_amount
    function test_SpendableAmountIfLimitDecreasedNotBelowSpentAmount() external {
        uint256 spending = 1 ether;
        uint256 spendable = 2 ether;
        uint256 newPeriodLimit = 2 ether;
        uint256 newSpendable = 1 ether;
        _givenLimitParametersSet(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), spendable, "spendableBalance");
        _assertPeriodSpending(spending, spendable);

        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(newPeriodLimit, PERIOD_DURATION);

        // the spent amount stays as it was and only the rest of the new limit is spendable
        _assertPeriodSpending(spending, newSpendable);
        assertEq(limitsChecker.spendableBalance(), newSpendable, "spendableBalance after the cut");

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(newSpendable);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);
    }

    // python: test_spendable_amount_renewal_if_period_duration_changed[3-2]
    function test_SpendableAmountRenewalIfPeriodDurationChangedFrom3To2() external {
        _givenLimitSpentAndPeriodDurationChanged(3, 2);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(2);

        _assertSpendableRenewed();
    }

    // python: test_spendable_amount_renewal_if_period_duration_changed[3-6]
    function test_SpendableAmountRenewalIfPeriodDurationChangedFrom3To6() external {
        _givenLimitSpentAndPeriodDurationChanged(3, 6);

        // the end of the old three-month period passes without renewing the spendable amount
        skip(MAX_SECONDS_IN_MONTH * 3);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);

        skip(MAX_SECONDS_IN_MONTH * (6 - 3));

        _assertSpendableRenewed();
    }

    // python: test_spendable_amount_renewal_if_period_duration_changed[12-1]
    function test_SpendableAmountRenewalIfPeriodDurationChangedFrom12To1() external {
        _givenLimitSpentAndPeriodDurationChanged(12, 1);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(1);

        _assertSpendableRenewed();
    }

    // python: test_spendable_amount_renewal_if_period_duration_changed[1-12]
    function test_SpendableAmountRenewalIfPeriodDurationChangedFrom1To12() external {
        _givenLimitSpentAndPeriodDurationChanged(1, 12);

        // the end of the old one-month period passes without renewing the spendable amount
        skip(MAX_SECONDS_IN_MONTH * 1);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);

        skip(MAX_SECONDS_IN_MONTH * (12 - 1));

        _assertSpendableRenewed();
    }

    // python: test_fail_if_update_spent_amount_when_no_period_duration_set
    function test_RevertWhen_UpdatingSpentAmountWithNoPeriodDurationSet() external {
        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("INVALID_PERIOD_DURATION");
        limitsChecker.updateSpentAmount(123);
    }

    // python: test_period_start_from_timestamp, period duration 1
    function test_PeriodStartFromTimestampForPeriodDuration1() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 1, 15),
            Calendar.timestampFromDate(2022, 1, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 1, 31, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 1, Calendar.timestampFromDate(2022, 1, 1));
    }

    // python: test_period_start_from_timestamp, period duration 2
    function test_PeriodStartFromTimestampForPeriodDuration2() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 3, 1),
            Calendar.timestampFromDate(2022, 3, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 4, 30, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 2, Calendar.timestampFromDate(2022, 3, 1));
    }

    // python: test_period_start_from_timestamp, period duration 3
    function test_PeriodStartFromTimestampForPeriodDuration3() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 6, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 6, 30, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 3, Calendar.timestampFromDate(2022, 4, 1));
    }

    // python: test_period_start_from_timestamp, period duration 6
    function test_PeriodStartFromTimestampForPeriodDuration6() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 7, 1),
            Calendar.timestampFromDate(2022, 7, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 10, 1),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 6, Calendar.timestampFromDate(2022, 7, 1));
    }

    // python: test_period_start_from_timestamp, period duration 12
    function test_PeriodStartFromTimestampForPeriodDuration12() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 12, Calendar.timestampFromDate(2022, 1, 1));
    }

    // python: test_period_end_from_timestamp, period duration 1
    function test_PeriodEndFromTimestampForPeriodDuration1() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 1, 15),
            Calendar.timestampFromDate(2022, 1, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 1, 31, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 1, Calendar.timestampFromDate(2022, 2, 1));
    }

    // python: test_period_end_from_timestamp, period duration 2
    function test_PeriodEndFromTimestampForPeriodDuration2() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 3, 1),
            Calendar.timestampFromDate(2022, 3, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 4, 30, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 2, Calendar.timestampFromDate(2022, 5, 1));
    }

    // python: test_period_end_from_timestamp, period duration 3
    function test_PeriodEndFromTimestampForPeriodDuration3() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 6, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 6, 30, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 3, Calendar.timestampFromDate(2022, 7, 1));
    }

    // python: test_period_end_from_timestamp, period duration 6
    function test_PeriodEndFromTimestampForPeriodDuration6() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 7, 1),
            Calendar.timestampFromDate(2022, 7, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 10, 1),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 6, Calendar.timestampFromDate(2023, 1, 1));
    }

    // python: test_period_end_from_timestamp, period duration 12
    function test_PeriodEndFromTimestampForPeriodDuration12() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 12, Calendar.timestampFromDate(2023, 1, 1));
    }

    function _givenLimitParametersSet(uint256 limit, uint256 periodDurationMonths) private {
        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(limit, periodDurationMonths);
    }

    /// @dev The whole limit is spent in a period of `initialPeriodDuration` months, then the
    /// duration changes to `newPeriodDuration`, which on its own renews nothing
    function _givenLimitSpentAndPeriodDurationChanged(
        uint256 initialPeriodDuration,
        uint256 newPeriodDuration
    ) private {
        uint256 spending = 3 ether;
        _givenLimitParametersSet(PERIOD_LIMIT, initialPeriodDuration);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(
            initialPeriodDuration > newPeriodDuration ? initialPeriodDuration : newPeriodDuration
        );

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), 0, "spendableBalance");
        _assertPeriodSpending(spending, 0);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);

        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(PERIOD_LIMIT, newPeriodDuration);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);
    }

    function _assertLimitParameters(uint256 expectedLimit, uint256 expectedPeriodDurationMonths)
        private
        view
    {
        (uint256 limit, uint256 periodDurationMonths) = limitsChecker.getLimitParameters();
        assertEq(limit, expectedLimit, "limit");
        assertEq(periodDurationMonths, expectedPeriodDurationMonths, "periodDurationMonths");
    }

    function _assertPeriodSpending(
        uint256 expectedAlreadySpentAmount,
        uint256 expectedSpendableBalanceInPeriod
    ) private view {
        (uint256 alreadySpentAmount, uint256 spendableBalanceInPeriod,,) =
            limitsChecker.getPeriodState();
        assertEq(alreadySpentAmount, expectedAlreadySpentAmount, "_alreadySpentAmount");
        assertEq(
            spendableBalanceInPeriod, expectedSpendableBalanceInPeriod, "_spendableBalanceInPeriod"
        );
    }

    /// @dev The whole limit is spendable again and nothing beyond it
    function _assertSpendableRenewed() private {
        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(PERIOD_LIMIT);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);
    }

    function _assertRevertOnPeriodDuration(uint256 periodDuration) private {
        vm.prank(setParametersRoleHolder);
        vm.expectRevert("INVALID_PERIOD_DURATION");
        limitsChecker.setLimitParameters(1 ether, periodDuration);
    }

    function _assertFirstMonthInPeriodForEveryMonth(uint256 periodDuration) private {
        vm.prank(setParametersRoleHolder);
        limitsCheckerWithPrivateViewsExposed.setLimitParameters(0, periodDuration);

        for (uint256 month = 1; month <= Calendar.MONTHS_PER_YEAR; ++month) {
            assertEq(
                limitsCheckerWithPrivateViewsExposed.getFirstMonthInPeriodFromCurrentMonth(month),
                TestHelpers.calcPeriodFirstMonth(periodDuration, month),
                "firstMonthInPeriod"
            );
        }
    }

    /// @dev Every input maps to `expectedResult`, and the probes an hour and a second outside the
    /// period map strictly before and after it
    function _assertPeriodStartFromTimestamp(
        uint256[5] memory inputs,
        uint256 periodDuration,
        uint256 expectedResult
    ) private {
        vm.prank(setParametersRoleHolder);
        limitsCheckerWithPrivateViewsExposed.setLimitParameters(PERIOD_LIMIT, periodDuration);

        for (uint256 i; i < inputs.length; ++i) {
            assertEq(
                limitsCheckerWithPrivateViewsExposed.getPeriodStartFromTimestamp(inputs[i]),
                expectedResult,
                "periodStart"
            );
        }

        assertLt(
            limitsCheckerWithPrivateViewsExposed.getPeriodStartFromTimestamp(inputs[0] - 1 hours),
            expectedResult,
            "periodStart an hour before"
        );
        assertLt(
            limitsCheckerWithPrivateViewsExposed.getPeriodStartFromTimestamp(inputs[0] - 1),
            expectedResult,
            "periodStart a second before"
        );
        assertGt(
            limitsCheckerWithPrivateViewsExposed.getPeriodStartFromTimestamp(inputs[4] + 1),
            expectedResult,
            "periodStart a second after"
        );
        assertGt(
            limitsCheckerWithPrivateViewsExposed.getPeriodStartFromTimestamp(inputs[4] + 1 hours),
            expectedResult,
            "periodStart an hour after"
        );
    }

    /// @dev As `_assertPeriodStartFromTimestamp`, with the Python's two-second probe after the period
    function _assertPeriodEndFromTimestamp(
        uint256[5] memory inputs,
        uint256 periodDuration,
        uint256 expectedResult
    ) private {
        vm.prank(setParametersRoleHolder);
        limitsCheckerWithPrivateViewsExposed.setLimitParameters(PERIOD_LIMIT, periodDuration);

        for (uint256 i; i < inputs.length; ++i) {
            assertEq(
                limitsCheckerWithPrivateViewsExposed.getPeriodEndFromTimestamp(inputs[i]),
                expectedResult,
                "periodEnd"
            );
        }

        assertLt(
            limitsCheckerWithPrivateViewsExposed.getPeriodEndFromTimestamp(inputs[0] - 1 hours),
            expectedResult,
            "periodEnd an hour before"
        );
        assertLt(
            limitsCheckerWithPrivateViewsExposed.getPeriodEndFromTimestamp(inputs[0] - 1),
            expectedResult,
            "periodEnd a second before"
        );
        assertGt(
            limitsCheckerWithPrivateViewsExposed.getPeriodEndFromTimestamp(inputs[4] + 2),
            expectedResult,
            "periodEnd two seconds after"
        );
        assertGt(
            limitsCheckerWithPrivateViewsExposed.getPeriodEndFromTimestamp(inputs[4] + 1 hours),
            expectedResult,
            "periodEnd an hour after"
        );
    }

    function _addresses(address account) private pure returns (address[] memory addresses) {
        addresses = new address[](1);
        addresses[0] = account;
    }
}
