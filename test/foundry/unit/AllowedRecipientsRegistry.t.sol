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
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {Calendar} from "test/foundry/unit/helpers/Calendar.sol";
import {Roles} from "test/foundry/unit/helpers/Roles.sol";
import {TestHelpers} from "test/foundry/unit/helpers/TestHelpers.sol";

contract AllowedRecipientsRegistryTest is Test {
    string internal constant RECIPIENT_TITLE = "New Allowed Recipient";

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
            Arrays.list(addRecipientRoleHolder),
            Arrays.list(removeRecipientRoleHolder),
            Arrays.list(setParametersRoleHolder),
            Arrays.list(updateSpentAmountRoleHolder),
            bokkyPooBahsDateTimeContract
        );

        vm.label(address(bokkyPooBahsDateTimeContract), "BokkyPooBahsDateTimeContract");
        vm.label(address(allowedRecipientsRegistry), "AllowedRecipientsRegistry");
    }

    function test_SetsInitialState() external view {
        assertTrue(
            allowedRecipientsRegistry.hasRole(
                Roles.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, addRecipientRoleHolder
            ),
            "addRecipientRoleHolder role"
        );
        assertTrue(
            allowedRecipientsRegistry.hasRole(
                Roles.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, removeRecipientRoleHolder
            ),
            "removeRecipientRoleHolder role"
        );
        assertTrue(
            allowedRecipientsRegistry.hasRole(Roles.SET_PARAMETERS_ROLE, setParametersRoleHolder),
            "setParametersRoleHolder role"
        );
        assertTrue(
            allowedRecipientsRegistry.hasRole(
                Roles.UPDATE_SPENT_AMOUNT_ROLE, updateSpentAmountRoleHolder
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

    function test_DeploysWithZeroAdmin() external {
        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            address(0),
            Arrays.list(owner),
            Arrays.list(owner),
            Arrays.list(owner),
            Arrays.list(owner),
            bokkyPooBahsDateTimeContract
        );

        assertTrue(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), address(0)), "zero admin role");
    }

    function test_DeploysWithNoRoleHolders() external {
        address[] memory noHolders = new address[](0);

        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            owner, noHolders, noHolders, noHolders, noHolders, bokkyPooBahsDateTimeContract
        );

        assertTrue(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), owner), "owner admin role");
    }

    function test_DeploysWithZeroBokkyPooBahsDateTimeContract() external {
        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            owner,
            Arrays.list(owner),
            Arrays.list(owner),
            Arrays.list(owner),
            Arrays.list(owner),
            IBokkyPooBahsDateTimeContract(address(0))
        );

        assertEq(
            address(registry.bokkyPooBahsDateTimeContract()),
            address(0),
            "bokkyPooBahsDateTimeContract"
        );
    }

    function test_DoesNotShareRightsBetweenRoles() external {
        vm.prank(owner);
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            voting,
            Arrays.list(addRecipientRoleHolder),
            Arrays.list(removeRecipientRoleHolder),
            Arrays.list(setParametersRoleHolder),
            Arrays.list(updateSpentAmountRoleHolder),
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
                TestHelpers.accessRevertMessage(
                    callers[i], Roles.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE
                )
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
                TestHelpers.accessRevertMessage(
                    callers[i], Roles.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE
                )
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
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], Roles.SET_PARAMETERS_ROLE));
            registry.setLimitParameters(0, 1);

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], Roles.SET_PARAMETERS_ROLE));
            registry.setBokkyPooBahsDateTimeContract(address(0));

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], Roles.SET_PARAMETERS_ROLE));
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
            vm.expectRevert(
                TestHelpers.accessRevertMessage(callers[i], Roles.UPDATE_SPENT_AMOUNT_ROLE)
            );
            registry.updateSpentAmount(1);
        }
    }

    function test_GrantsRolesToMultipleHolders() external {
        address[20] memory accounts = _sweepAccounts();
        address[] memory addRecipientRoleHolders = Arrays.list(accounts[2], accounts[3]);
        address[] memory removeRecipientRoleHolders = Arrays.list(accounts[4], accounts[5]);
        address[] memory setParametersRoleHolders = Arrays.list(accounts[6], accounts[7]);
        address[] memory updateSpentAmountRoleHolders = Arrays.list(accounts[8], accounts[9]);

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
                TestHelpers.accessRevertMessage(
                    callers[i], Roles.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE
                )
            );
            registry.addRecipient(callers[i], RECIPIENT_TITLE);
        }

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
                TestHelpers.accessRevertMessage(
                    callers[i], Roles.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE
                )
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
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], Roles.SET_PARAMETERS_ROLE));
            registry.setLimitParameters(5, 1);

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], Roles.SET_PARAMETERS_ROLE));
            registry.setBokkyPooBahsDateTimeContract(address(0));

            vm.prank(callers[i]);
            vm.expectRevert(TestHelpers.accessRevertMessage(callers[i], Roles.SET_PARAMETERS_ROLE));
            registry.unsafeSetSpentAmount(0);
        }

        vm.prank(setParametersRoleHolders[0]);
        registry.setLimitParameters(5, 1);

        vm.prank(setParametersRoleHolders[1]);
        registry.setLimitParameters(5, 1);

        callers = _callersWithout(accounts, updateSpentAmountRoleHolders);
        for (uint256 i; i < callers.length; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(callers[i], Roles.UPDATE_SPENT_AMOUNT_ROLE)
            );
            registry.updateSpentAmount(1);
        }

        vm.prank(updateSpentAmountRoleHolders[0]);
        registry.updateSpentAmount(1);

        vm.prank(updateSpentAmountRoleHolders[1]);
        registry.updateSpentAmount(1);
    }

    function test_AddsRecipient() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, RECIPIENT_TITLE);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipient1), "isRecipientAllowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            Arrays.list(recipient1),
            "allowedRecipients"
        );
    }

    function test_AddsRecipientWithEmptyTitle() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(recipient1, "");

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(recipient1), "isRecipientAllowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            Arrays.list(recipient1),
            "allowedRecipients"
        );
    }

    function test_AddsRecipientWithZeroAddress() external {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(address(0), RECIPIENT_TITLE);

        assertTrue(allowedRecipientsRegistry.isRecipientAllowed(address(0)), "isRecipientAllowed");
        assertEq(
            allowedRecipientsRegistry.getAllowedRecipients(),
            Arrays.list(address(0)),
            "allowedRecipients"
        );
    }

    function test_AddsMultipleRecipients() external {
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
            Arrays.list(recipient1, recipient2),
            "allowedRecipients"
        );
    }

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

    function test_RemovesRecipient() external {
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

    function test_RemovesNotLastRecipientInTheList() external {
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
            Arrays.list(recipient2),
            "allowedRecipients"
        );
    }

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
            Arrays.list(recipient1),
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

    /// @dev The twenty accounts of the role sweep, the eight role holders at fixed indices
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
}

contract LimitsCheckerTest is Test {
    uint256 internal constant MAX_SECONDS_IN_MONTH = 31 days;
    uint256 internal constant PERIOD_LIMIT = 3 ether;
    uint256 internal constant PERIOD_DURATION = 1;
    uint256 internal constant INITIAL_LIMIT = 100 ether;
    uint256 internal constant INITIAL_PERIOD_DURATION = 3;

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
            Arrays.list(setParametersRoleHolder),
            Arrays.list(updateSpentAmountRoleHolder),
            bokkyPooBahsDateTimeContract
        );
        limitsCheckerWithPrivateViewsExposed = new LimitsCheckerWithPrivateViewsExposed(
            Arrays.list(setParametersRoleHolder),
            Arrays.list(updateSpentAmountRoleHolder),
            bokkyPooBahsDateTimeContract
        );
        vm.stopPrank();

        vm.label(address(bokkyPooBahsDateTimeContract), "BokkyPooBahsDateTimeContract");
        vm.label(address(limitsChecker), "LimitsChecker");
        vm.label(
            address(limitsCheckerWithPrivateViewsExposed), "LimitsCheckerWithPrivateViewsExposed"
        );
    }

    function test_RevertWhen_StrangerSetsLimitParameters() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, Roles.SET_PARAMETERS_ROLE));
        limitsChecker.setLimitParameters(123, 1);
    }

    function test_RevertWhen_StrangerSetsBokkyPooBahsDateTimeContract() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, Roles.SET_PARAMETERS_ROLE));
        limitsChecker.setBokkyPooBahsDateTimeContract(address(0));
    }

    function test_RevertWhen_StrangerUnsafeSetsSpentAmount() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, Roles.SET_PARAMETERS_ROLE));
        limitsChecker.unsafeSetSpentAmount(0);
    }

    function test_RevertWhen_StrangerUpdatesSpentAmount() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, Roles.UPDATE_SPENT_AMOUNT_ROLE));
        limitsChecker.updateSpentAmount(123);
    }

    function test_SetsDateTimeContract() external {
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

    function test_RevertWhen_SettingTheSameDateTimeContract() external {
        address currentAddress = address(limitsChecker.bokkyPooBahsDateTimeContract());

        vm.prank(setParametersRoleHolder);
        vm.expectRevert("SAME_DATE_TIME_CONTRACT_ADDRESS");
        limitsChecker.setBokkyPooBahsDateTimeContract(currentAddress);
    }

    function test_RevertWhen_UnsafeSetSpentAmountExceedsLimit() external {
        _setLimitParameters(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);

        _assertLimitParameters(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);
        (uint256 alreadySpentAmount,,,) = limitsChecker.getPeriodState();
        assertEq(alreadySpentAmount, 0, "_alreadySpentAmount");

        vm.prank(setParametersRoleHolder);
        vm.expectRevert("ERROR_SPENT_AMOUNT_EXCEEDS_LIMIT");
        limitsChecker.unsafeSetSpentAmount(INITIAL_LIMIT + 1);
    }

    function test_SetsSpentAmountUnsafelyWhenNewSpentAmountIsTheSame() external {
        _setLimitParameters(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);

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

    function test_SetsSpentAmountUnsafely() external {
        _setLimitParameters(INITIAL_LIMIT, INITIAL_PERIOD_DURATION);

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

    function test_SetsLimitParameters() external {
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

    function test_ComputesPeriodRangeForAllAllowedPeriodDurations() external {
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

    function test_RevertWhen_PeriodDurationIs0() external {
        _assertRevertOnPeriodDuration(0);
    }

    function test_RevertWhen_PeriodDurationIs4() external {
        _assertRevertOnPeriodDuration(4);
    }

    function test_RevertWhen_PeriodDurationIs5() external {
        _assertRevertOnPeriodDuration(5);
    }

    function test_RevertWhen_PeriodDurationIs7() external {
        _assertRevertOnPeriodDuration(7);
    }

    function test_RevertWhen_PeriodDurationIs8() external {
        _assertRevertOnPeriodDuration(8);
    }

    function test_RevertWhen_PeriodDurationIs9() external {
        _assertRevertOnPeriodDuration(9);
    }

    function test_RevertWhen_PeriodDurationIs10() external {
        _assertRevertOnPeriodDuration(10);
    }

    function test_RevertWhen_PeriodDurationIs11() external {
        _assertRevertOnPeriodDuration(11);
    }

    function test_RevertWhen_PeriodDurationIs13() external {
        _assertRevertOnPeriodDuration(13);
    }

    function test_RevertWhen_PeriodDurationIs14() external {
        _assertRevertOnPeriodDuration(14);
    }

    function test_RevertWhen_PeriodDurationIs100500() external {
        _assertRevertOnPeriodDuration(100500);
    }

    function test_ComputesFirstMonthInPeriodForPeriodDuration1() external {
        _assertFirstMonthInPeriodForEveryMonth(1);
    }

    function test_ComputesFirstMonthInPeriodForPeriodDuration2() external {
        _assertFirstMonthInPeriodForEveryMonth(2);
    }

    function test_ComputesFirstMonthInPeriodForPeriodDuration3() external {
        _assertFirstMonthInPeriodForEveryMonth(3);
    }

    function test_ComputesFirstMonthInPeriodForPeriodDuration6() external {
        _assertFirstMonthInPeriodForEveryMonth(6);
    }

    function test_ComputesFirstMonthInPeriodForPeriodDuration12() external {
        _assertFirstMonthInPeriodForEveryMonth(12);
    }

    function test_RevertWhen_LimitIsGreaterThanMaxLimit() external {
        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(2 ** 128 - 1, PERIOD_DURATION);

        vm.prank(setParametersRoleHolder);
        vm.expectRevert("TOO_LARGE_LIMIT");
        limitsChecker.setLimitParameters(2 ** 128, PERIOD_DURATION);
    }

    function test_KeepsReportingOldPeriodUntilAdvanced() external {
        uint256 periodLimit = 10 ether;
        uint256 payoutAmount = 3 ether;
        uint256 spendableBalance = periodLimit - payoutAmount;
        _setLimitParameters(periodLimit, PERIOD_DURATION);

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

    function test_UpdatesSpentAmountWithinTheLimit() external {
        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        uint256 periodStart = TestHelpers.getMonthStartTimestamp(block.timestamp);
        uint256 periodEnd = TestHelpers.getMonthStartTimestamp(
            TestHelpers.getDateInNextPeriod(block.timestamp, PERIOD_DURATION)
        );
        uint256 spending = 2 ether;
        uint256 spendable = PERIOD_LIMIT - spending;
        _setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

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

    function test_UpdatesSpentAmountPreciselyToTheLimitInMultiplePortions() external {
        uint256 spending = 1 ether;
        uint256 spendable = PERIOD_LIMIT - spending;
        _setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

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

        _assertPeriodSpending(2 * spending, PERIOD_LIMIT - 2 * spending);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        _assertPeriodSpending(PERIOD_LIMIT, 0);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);
    }

    function test_RestoresSpendingAmountInTheNextPeriod() external {
        uint256 spending = PERIOD_LIMIT;
        uint256 spendable = PERIOD_LIMIT - spending;
        _setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), spendable, "spendableBalance");

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(spending);

        skip(MAX_SECONDS_IN_MONTH);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), spendable, "spendableBalance in the next period");
    }

    function test_RevertWhen_UpdatingSpentAmountBeyondTheLimit() external {
        _setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        (, uint256 spendableBalance,,) = limitsChecker.getPeriodState();
        assertEq(spendableBalance, PERIOD_LIMIT, "_spendableBalanceInPeriod");

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(PERIOD_LIMIT + 1);
    }

    function test_IncreasesSpendableAmountWhenLimitIncreases() external {
        uint256 spending = PERIOD_LIMIT;
        uint256 spendable = PERIOD_LIMIT - spending;
        uint256 newPeriodLimit = 2 * PERIOD_LIMIT;
        uint256 newSpendable = spendable + (newPeriodLimit - PERIOD_LIMIT);
        _setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(PERIOD_DURATION);

        vm.prank(updateSpentAmountRoleHolder);
        limitsChecker.updateSpentAmount(spending);

        assertEq(limitsChecker.spendableBalance(), spendable, "spendableBalance");
        _assertPeriodSpending(spending, spendable);

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

    function test_ZeroesSpendableAmountWhenLimitDecreasesBelowSpentAmount() external {
        uint256 spending = 1 ether;
        uint256 spendable = PERIOD_LIMIT - spending;
        uint256 newPeriodLimit = spending - 1;
        _setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

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

    function test_ReducesSpendableAmountWhenLimitDecreasesNotBelowSpentAmount() external {
        uint256 spending = 1 ether;
        uint256 spendable = PERIOD_LIMIT - spending;
        uint256 newPeriodLimit = 2 * spending;
        uint256 newSpendable = newPeriodLimit - spending;
        _setLimitParameters(PERIOD_LIMIT, PERIOD_DURATION);

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

    function test_RenewsSpendableAmountWhenPeriodDurationChangesFrom3To2() external {
        _spendLimitAndChangePeriodDuration(3, 2);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(2);

        _assertSpendableRenewed();
    }

    function test_RenewsSpendableAmountWhenPeriodDurationChangesFrom3To6() external {
        _spendLimitAndChangePeriodDuration(3, 6);

        // the end of the old three-month period passes without renewing the spendable amount
        skip(MAX_SECONDS_IN_MONTH * 3);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);

        skip(MAX_SECONDS_IN_MONTH * (6 - 3));

        _assertSpendableRenewed();
    }

    function test_RenewsSpendableAmountWhenPeriodDurationChangesFrom12To1() external {
        _spendLimitAndChangePeriodDuration(12, 1);

        TestHelpers.advanceChainTimeToBeginningOfTheNextPeriod(1);

        _assertSpendableRenewed();
    }

    function test_RenewsSpendableAmountWhenPeriodDurationChangesFrom1To12() external {
        _spendLimitAndChangePeriodDuration(1, 12);

        // the end of the old one-month period passes without renewing the spendable amount
        skip(MAX_SECONDS_IN_MONTH * 1);

        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        limitsChecker.updateSpentAmount(1);

        skip(MAX_SECONDS_IN_MONTH * (12 - 1));

        _assertSpendableRenewed();
    }

    function test_RevertWhen_UpdatingSpentAmountWithNoPeriodDurationSet() external {
        vm.prank(updateSpentAmountRoleHolder);
        vm.expectRevert("INVALID_PERIOD_DURATION");
        limitsChecker.updateSpentAmount(123);
    }

    function test_ComputesPeriodStartFromTimestampForPeriodDuration1() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 1, 15),
            Calendar.timestampFromDate(2022, 1, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 1, 31, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 1, Calendar.timestampFromDate(2022, 1, 1));
    }

    function test_ComputesPeriodStartFromTimestampForPeriodDuration2() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 3, 1),
            Calendar.timestampFromDate(2022, 3, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 4, 30, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 2, Calendar.timestampFromDate(2022, 3, 1));
    }

    function test_ComputesPeriodStartFromTimestampForPeriodDuration3() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 6, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 6, 30, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 3, Calendar.timestampFromDate(2022, 4, 1));
    }

    function test_ComputesPeriodStartFromTimestampForPeriodDuration6() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 7, 1),
            Calendar.timestampFromDate(2022, 7, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 10, 1),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 6, Calendar.timestampFromDate(2022, 7, 1));
    }

    function test_ComputesPeriodStartFromTimestampForPeriodDuration12() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodStartFromTimestamp(inputs, 12, Calendar.timestampFromDate(2022, 1, 1));
    }

    function test_ComputesPeriodEndFromTimestampForPeriodDuration1() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 1, 15),
            Calendar.timestampFromDate(2022, 1, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 1, 31, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 1, Calendar.timestampFromDate(2022, 2, 1));
    }

    function test_ComputesPeriodEndFromTimestampForPeriodDuration2() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 3, 1),
            Calendar.timestampFromDate(2022, 3, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 4, 30, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 2, Calendar.timestampFromDate(2022, 5, 1));
    }

    function test_ComputesPeriodEndFromTimestampForPeriodDuration3() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 4, 1),
            Calendar.timestampFromDate(2022, 4, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 6, 30, 23, 0, 0),
            Calendar.timestampFromDate(2022, 6, 30, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 3, Calendar.timestampFromDate(2022, 7, 1));
    }

    function test_ComputesPeriodEndFromTimestampForPeriodDuration6() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 7, 1),
            Calendar.timestampFromDate(2022, 7, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 10, 1),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 6, Calendar.timestampFromDate(2023, 1, 1));
    }

    function test_ComputesPeriodEndFromTimestampForPeriodDuration12() external {
        uint256[5] memory inputs = [
            Calendar.timestampFromDate(2022, 1, 1),
            Calendar.timestampFromDate(2022, 1, 1, 1, 0, 0),
            Calendar.timestampFromDate(2022, 5, 15),
            Calendar.timestampFromDate(2022, 12, 31, 23, 0, 0),
            Calendar.timestampFromDate(2022, 12, 31, 23, 59, 59)
        ];

        _assertPeriodEndFromTimestamp(inputs, 12, Calendar.timestampFromDate(2023, 1, 1));
    }

    function _setLimitParameters(uint256 limit, uint256 periodDurationMonths) private {
        vm.prank(setParametersRoleHolder);
        limitsChecker.setLimitParameters(limit, periodDurationMonths);
    }

    /// @dev The whole limit is spent in a period of `initialPeriodDuration` months, then the
    /// duration changes to `newPeriodDuration`, which on its own renews nothing
    function _spendLimitAndChangePeriodDuration(
        uint256 initialPeriodDuration,
        uint256 newPeriodDuration
    ) private {
        uint256 spending = PERIOD_LIMIT;
        _setLimitParameters(PERIOD_LIMIT, initialPeriodDuration);

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
}
