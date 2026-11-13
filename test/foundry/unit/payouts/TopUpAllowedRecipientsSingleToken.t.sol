// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    TopUpAllowedRecipientsSingleToken
} from "contracts/payouts/single-token/TopUpAllowedRecipientsSingleToken.sol";
import {AllowedRecipientsRegistry} from "contracts/AllowedRecipientsRegistry.sol";
import {EasyTrack} from "contracts/EasyTrack.sol";
import {IFinance} from "contracts/interfaces/IFinance.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {Constants} from "test/foundry/unit/helpers/Constants.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {
    BokkyPooBahsDateTimeContract
} from "test/foundry/unit/stubs/BokkyPooBahsDateTimeContract.sol";
import {MiniMeTokenStub} from "test/foundry/unit/stubs/MiniMeTokenStub.sol";

contract TopUpAllowedRecipientsSingleTokenTest is Test {
    /// @dev The reference `createEVMScript` attaches to every payment
    string internal constant PAYMENT_REFERENCE = "Easy Track: top up recipient";

    uint256 internal constant LIMIT = 100 ether;
    uint256 internal constant PERIOD_DURATION_MONTHS = 12;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");
    address internal finance = makeAddr("finance");
    address internal trustedCaller = makeAddr("trustedCaller");
    address internal recipient = makeAddr("recipient");
    address internal secondRecipient = makeAddr("secondRecipient");
    address internal addRecipientRoleHolder = makeAddr("addRecipientRoleHolder");
    address internal removeRecipientRoleHolder = makeAddr("removeRecipientRoleHolder");
    address internal setLimitRoleHolder = makeAddr("setLimitRoleHolder");
    address internal updateSpentRoleHolder = makeAddr("updateSpentRoleHolder");

    MiniMeTokenStub internal ldo;
    EasyTrack internal easyTrack;
    BokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;
    AllowedRecipientsRegistry internal allowedRecipientsRegistry;
    TopUpAllowedRecipientsSingleToken internal topUpAllowedRecipientsSingleToken;

    function setUp() public {
        bokkyPooBahsDateTimeContract = new BokkyPooBahsDateTimeContract();

        vm.startPrank(owner);
        ldo = new MiniMeTokenStub();
        easyTrack = new EasyTrack(
            address(ldo),
            voting,
            Constants.MIN_MOTION_DURATION,
            Constants.MAX_MOTIONS_LIMIT,
            Constants.DEFAULT_OBJECTIONS_THRESHOLD
        );
        allowedRecipientsRegistry = new AllowedRecipientsRegistry(
            owner,
            Arrays.list(addRecipientRoleHolder),
            Arrays.list(removeRecipientRoleHolder),
            Arrays.list(setLimitRoleHolder),
            Arrays.list(updateSpentRoleHolder),
            bokkyPooBahsDateTimeContract
        );
        topUpAllowedRecipientsSingleToken = new TopUpAllowedRecipientsSingleToken(
            trustedCaller,
            address(allowedRecipientsRegistry),
            finance,
            address(ldo),
            address(easyTrack)
        );
        vm.stopPrank();

        vm.label(address(easyTrack), "easyTrack");
        vm.label(address(bokkyPooBahsDateTimeContract), "bokkyPooBahsDateTimeContract");
        vm.label(address(allowedRecipientsRegistry), "allowedRecipientsRegistry");
        vm.label(address(topUpAllowedRecipientsSingleToken), "topUpAllowedRecipientsSingleToken");
    }

    function test_SetsInitialState() external {
        vm.prank(owner);
        TopUpAllowedRecipientsSingleToken topUpFactory = new TopUpAllowedRecipientsSingleToken(
            trustedCaller,
            address(allowedRecipientsRegistry),
            finance,
            address(ldo),
            address(easyTrack)
        );

        assertEq(topUpFactory.token(), address(ldo), "token");
        assertEq(
            address(topUpFactory.allowedRecipientsRegistry()),
            address(allowedRecipientsRegistry),
            "allowedRecipientsRegistry"
        );
        assertEq(topUpFactory.trustedCaller(), trustedCaller, "trustedCaller");
        assertEq(address(topUpFactory.easyTrack()), address(easyTrack), "easyTrack");
        assertEq(address(topUpFactory.finance()), finance, "finance");
    }

    function test_RevertWhen_TrustedCallerIsZero() external {
        vm.expectRevert("TRUSTED_CALLER_IS_ZERO_ADDRESS");
        new TopUpAllowedRecipientsSingleToken(
            address(0),
            address(allowedRecipientsRegistry),
            finance,
            address(ldo),
            address(easyTrack)
        );
    }

    function test_DeploysWithZeroAddresses() external {
        vm.prank(owner);
        TopUpAllowedRecipientsSingleToken topUpFactory = new TopUpAllowedRecipientsSingleToken(
            trustedCaller, address(0), address(0), address(0), address(0)
        );

        assertEq(topUpFactory.trustedCaller(), trustedCaller, "trustedCaller");
        assertEq(
            address(topUpFactory.allowedRecipientsRegistry()),
            address(0),
            "allowedRecipientsRegistry"
        );
        assertEq(address(topUpFactory.finance()), address(0), "finance");
        assertEq(topUpFactory.token(), address(0), "token");
        assertEq(address(topUpFactory.easyTrack()), address(0), "easyTrack");
    }

    function test_RevertWhen_CreatorIsNotTrustedCaller() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            stranger, _callData(new address[](0), new uint256[](0))
        );
    }

    function test_CreatesEVMScriptFromAnyCaller() external {
        _allowRecipient(stranger, "Test Recipient");
        _setLimit(LIMIT);

        vm.prank(stranger);
        bytes memory evmScript = topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(Arrays.list(stranger), Arrays.list(123))
        );

        address[] memory targets = Arrays.list(address(allowedRecipientsRegistry), finance);
        bytes[] memory datas = Arrays.list(
            abi.encodeWithSelector(allowedRecipientsRegistry.updateSpentAmount.selector, 123),
            _newImmediatePaymentCallData(stranger, 123)
        );

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    function test_DecodesEVMScriptCallDataFromAnyCaller() external {
        vm.prank(stranger);
        (address[] memory recipients, uint256[] memory amounts) = topUpAllowedRecipientsSingleToken.decodeEVMScriptCallData(
            _callData(Arrays.list(stranger), Arrays.list(123))
        );

        assertEq(recipients, Arrays.list(stranger), "recipients");
        assertEq(amounts, Arrays.list(123), "amounts");
    }

    function test_RevertWhen_LengthMismatch() external {
        vm.expectRevert("LENGTH_MISMATCH");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(Arrays.list(recipient), new uint256[](0))
        );

        vm.expectRevert("LENGTH_MISMATCH");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(new address[](0), Arrays.list(123))
        );
    }

    function test_RevertWhen_DataIsEmpty() external {
        vm.expectRevert("EMPTY_DATA");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(new address[](0), new uint256[](0))
        );
    }

    function test_RevertWhen_AmountIsZero() external {
        _allowRecipient(recipient, "Test Recipient");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        vm.expectRevert("ZERO_AMOUNT");
        topUpFactory.createEVMScript(
            owner, _callData(Arrays.list(recipient), Arrays.list(uint256(0)))
        );

        vm.expectRevert("ZERO_AMOUNT");
        topUpFactory.createEVMScript(
            owner, _callData(Arrays.list(recipient, recipient), Arrays.list(123, 0))
        );
    }

    function test_RevertWhen_RecipientIsNotAllowed() external {
        _allowRecipient(recipient, "Test Recipient");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        vm.expectRevert("RECIPIENT_NOT_ALLOWED");
        topUpFactory.createEVMScript(owner, _callData(Arrays.list(stranger), Arrays.list(123)));
    }

    function test_CreatesEVMScriptForSingleRecipient() external {
        _allowRecipient(recipient, "Test Recipient");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        address[] memory recipients = Arrays.list(recipient);
        uint256[] memory amounts = Arrays.list(1 ether);
        bytes memory callData = _callData(recipients, amounts);

        bytes memory evmScript = topUpFactory.createEVMScript(owner, callData);

        (address[] memory decodedRecipients, uint256[] memory decodedAmounts) =
            topUpFactory.decodeEVMScriptCallData(callData);

        assertEq(decodedRecipients, recipients, "recipients");
        assertEq(decodedAmounts, amounts, "amounts");
        assertTrue(
            _contains(evmScript, bytes(PAYMENT_REFERENCE)), "evmScript carries the reference"
        );
    }

    function test_CreatesEVMScriptForMultipleRecipients() external {
        _allowRecipient(recipient, "Test Recipient 1");
        _allowRecipient(secondRecipient, "Test Recipient 2");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        address[] memory recipients = Arrays.list(recipient, secondRecipient);
        uint256[] memory amounts = Arrays.list(1 ether, 2 ether);
        bytes memory callData = _callData(recipients, amounts);

        bytes memory evmScript = topUpFactory.createEVMScript(owner, callData);

        (address[] memory decodedRecipients, uint256[] memory decodedAmounts) =
            topUpFactory.decodeEVMScriptCallData(callData);

        assertEq(decodedRecipients, recipients, "recipients");
        assertEq(decodedAmounts, amounts, "amounts");
        assertTrue(
            _contains(evmScript, bytes(PAYMENT_REFERENCE)), "evmScript carries the reference"
        );
    }

    function test_RevertWhen_SumExceedsLimit() external {
        _allowRecipient(recipient, "Test Recipient 1");
        _allowRecipient(secondRecipient, "Test Recipient 2");
        _setLimit(20 ether);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        topUpFactory.createEVMScript(
            owner,
            _callData(Arrays.list(recipient, secondRecipient), Arrays.list(10 ether, 20 ether))
        );
    }

    function test_CreatesEVMScript() external {
        _allowRecipient(recipient, "Test Recipient 1");
        _allowRecipient(secondRecipient, "Test Recipient 2");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        bytes memory evmScript = topUpFactory.createEVMScript(
            owner, _callData(Arrays.list(recipient, secondRecipient), Arrays.list(1 ether, 2 ether))
        );

        address[] memory targets = Arrays.list(address(allowedRecipientsRegistry), finance, finance);
        bytes[] memory datas = Arrays.list(
            abi.encodeWithSelector(allowedRecipientsRegistry.updateSpentAmount.selector, 3 ether),
            _newImmediatePaymentCallData(recipient, 1 ether),
            _newImmediatePaymentCallData(secondRecipient, 2 ether)
        );

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    function test_DecodesEVMScriptCallData() external view {
        (address[] memory recipients, uint256[] memory amounts) = topUpAllowedRecipientsSingleToken.decodeEVMScriptCallData(
            _callData(Arrays.list(recipient), Arrays.list(1 ether))
        );

        assertEq(recipients, Arrays.list(recipient), "recipients");
        assertEq(amounts, Arrays.list(1 ether), "amounts");
    }

    function _allowRecipient(address allowed, string memory title) private {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(allowed, title);
    }

    function _setLimit(uint256 limit) private {
        vm.prank(setLimitRoleHolder);
        allowedRecipientsRegistry.setLimitParameters(limit, PERIOD_DURATION_MONTHS);
    }

    function _deployTopUpFactoryTrustedByOwner()
        private
        returns (TopUpAllowedRecipientsSingleToken)
    {
        vm.prank(owner);
        return new TopUpAllowedRecipientsSingleToken(
            owner, address(allowedRecipientsRegistry), finance, address(ldo), address(easyTrack)
        );
    }

    function _callData(address[] memory recipients, uint256[] memory amounts)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(recipients, amounts);
    }

    function _newImmediatePaymentCallData(address receiver, uint256 amount)
        private
        view
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            IFinance.newImmediatePayment.selector, address(ldo), receiver, amount, PAYMENT_REFERENCE
        );
    }

    function _contains(bytes memory haystack, bytes memory needle) private pure returns (bool) {
        for (uint256 start; start + needle.length <= haystack.length; ++start) {
            bool matched = true;

            for (uint256 i; i < needle.length && matched; ++i) {
                matched = haystack[start + i] == needle[i];
            }

            if (matched) return true;
        }

        return false;
    }
}
