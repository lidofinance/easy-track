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
            _addresses(addRecipientRoleHolder),
            _addresses(removeRecipientRoleHolder),
            _addresses(setLimitRoleHolder),
            _addresses(updateSpentRoleHolder),
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

    // python: test_top_up_factory_initial_state
    function test_TopUpFactoryInitialState() external {
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

    // python: test_fail_if_zero_trusted_caller
    function test_RevertWhen_TrustedCallerIsZeroAddress() external {
        vm.expectRevert("TRUSTED_CALLER_IS_ZERO_ADDRESS");
        new TopUpAllowedRecipientsSingleToken(
            address(0),
            address(allowedRecipientsRegistry),
            finance,
            address(ldo),
            address(easyTrack)
        );
    }

    // python: test_top_up_factory_constructor_zero_argument_addresses_allowed
    function test_DeploysWithZeroArgumentAddresses() external {
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

    // python: test_fail_create_evm_script_if_not_trusted_caller
    function test_RevertWhen_CreatorIsNotTrustedCaller() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            stranger, _callData(new address[](0), new uint256[](0))
        );
    }

    // python: test_create_evm_script_is_permissionless
    function test_CreateEVMScriptIsPermissionless() external {
        _allowRecipient(stranger, "Test Recipient");
        _setLimit(LIMIT);

        vm.prank(stranger);
        bytes memory evmScript = topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(_addresses(stranger), _amounts(123))
        );

        address[] memory targets = _addresses(address(allowedRecipientsRegistry), finance);
        bytes[] memory datas = new bytes[](2);
        datas[0] = abi.encodeWithSelector(allowedRecipientsRegistry.updateSpentAmount.selector, 123);
        datas[1] = _newImmediatePaymentCallData(stranger, 123);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_calldata_is_permissionless
    function test_DecodeEVMScriptCallDataIsPermissionless() external {
        vm.prank(stranger);
        (address[] memory recipients, uint256[] memory amounts) = topUpAllowedRecipientsSingleToken.decodeEVMScriptCallData(
            _callData(_addresses(stranger), _amounts(123))
        );

        assertEq(recipients, _addresses(stranger), "recipients");
        assertEq(amounts, _amounts(123), "amounts");
    }

    // python: test_fail_create_evm_script_if_length_mismatch
    function test_RevertWhen_LengthMismatch() external {
        vm.expectRevert("LENGTH_MISMATCH");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(_addresses(recipient), new uint256[](0))
        );

        vm.expectRevert("LENGTH_MISMATCH");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(new address[](0), _amounts(123))
        );
    }

    // python: test_fail_create_evm_script_if_empty_data
    function test_RevertWhen_DataIsEmpty() external {
        vm.expectRevert("EMPTY_DATA");
        topUpAllowedRecipientsSingleToken.createEVMScript(
            trustedCaller, _callData(new address[](0), new uint256[](0))
        );
    }

    // python: test_fail_create_evm_script_if_zero_amount
    function test_RevertWhen_AmountIsZero() external {
        _allowRecipient(recipient, "Test Recipient");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        vm.expectRevert("ZERO_AMOUNT");
        topUpFactory.createEVMScript(owner, _callData(_addresses(recipient), _amounts(0)));

        vm.expectRevert("ZERO_AMOUNT");
        topUpFactory.createEVMScript(
            owner, _callData(_addresses(recipient, recipient), _amounts(123, 0))
        );
    }

    // python: test_fail_create_evm_script_if_recipient_not_allowed
    function test_RevertWhen_RecipientIsNotAllowed() external {
        _allowRecipient(recipient, "Test Recipient");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        vm.expectRevert("RECIPIENT_NOT_ALLOWED");
        topUpFactory.createEVMScript(owner, _callData(_addresses(stranger), _amounts(123)));
    }

    // python: test_top_up_factory_evm_script_creation_happy_path
    function test_TopUpFactoryEVMScriptCreationHappyPath() external {
        _allowRecipient(recipient, "Test Recipient");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        address[] memory recipients = _addresses(recipient);
        uint256[] memory amounts = _amounts(1 ether);
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

    // python: test_top_up_factory_evm_script_creation_multiple_recipients_happy_path
    function test_TopUpFactoryEVMScriptCreationMultipleRecipientsHappyPath() external {
        _allowRecipient(recipient, "Test Recipient 1");
        _allowRecipient(secondRecipient, "Test Recipient 2");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        address[] memory recipients = _addresses(recipient, secondRecipient);
        uint256[] memory amounts = _amounts(1 ether, 2 ether);
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

    // python: test_fail_create_evm_script_if_sum_exceeds_limit
    function test_RevertWhen_SumExceedsLimit() external {
        _allowRecipient(recipient, "Test Recipient 1");
        _allowRecipient(secondRecipient, "Test Recipient 2");
        _setLimit(20 ether);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        vm.expectRevert("SUM_EXCEEDS_SPENDABLE_BALANCE");
        topUpFactory.createEVMScript(
            owner, _callData(_addresses(recipient, secondRecipient), _amounts(10 ether, 20 ether))
        );
    }

    // python: test_create_evm_script_correctly
    function test_CreatesEVMScript() external {
        _allowRecipient(recipient, "Test Recipient 1");
        _allowRecipient(secondRecipient, "Test Recipient 2");
        _setLimit(LIMIT);
        TopUpAllowedRecipientsSingleToken topUpFactory = _deployTopUpFactoryTrustedByOwner();

        bytes memory evmScript = topUpFactory.createEVMScript(
            owner, _callData(_addresses(recipient, secondRecipient), _amounts(1 ether, 2 ether))
        );

        address[] memory targets = _addresses(address(allowedRecipientsRegistry), finance, finance);
        bytes[] memory datas = new bytes[](3);
        datas[0] =
            abi.encodeWithSelector(allowedRecipientsRegistry.updateSpentAmount.selector, 3 ether);
        datas[1] = _newImmediatePaymentCallData(recipient, 1 ether);
        datas[2] = _newImmediatePaymentCallData(secondRecipient, 2 ether);

        assertEq(evmScript, EVMScripts.encodeCallScript(targets, datas), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        (address[] memory recipients, uint256[] memory amounts) = topUpAllowedRecipientsSingleToken.decodeEVMScriptCallData(
            _callData(_addresses(recipient), _amounts(1 ether))
        );

        assertEq(recipients, _addresses(recipient), "recipients");
        assertEq(amounts, _amounts(1 ether), "amounts");
    }

    /// @dev python: registry.addRecipient(recipient, title) from add_recipient_role_holder
    function _allowRecipient(address allowed, string memory title) private {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(allowed, title);
    }

    /// @dev python: registry.setLimitParameters(limit, 12) from set_limit_role_holder
    function _setLimit(uint256 limit) private {
        vm.prank(setLimitRoleHolder);
        allowedRecipientsRegistry.setLimitParameters(limit, PERIOD_DURATION_MONTHS);
    }

    /// @dev python: owner.deploy(TopUpAllowedRecipientsSingleToken, owner, registry, finance, ldo,
    /// easy_track), the factory the creation tests drive with `owner` as its trusted caller
    function _deployTopUpFactoryTrustedByOwner()
        private
        returns (TopUpAllowedRecipientsSingleToken)
    {
        vm.prank(owner);
        return new TopUpAllowedRecipientsSingleToken(
            owner, address(allowedRecipientsRegistry), finance, address(ldo), address(easyTrack)
        );
    }

    /// @dev python: C(recipients, amounts) = encode_calldata(["address[]", "uint256[]"], ...)
    function _callData(address[] memory recipients, uint256[] memory amounts)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(recipients, amounts);
    }

    /// @dev python: finance.newImmediatePayment.encode_input(ldo, recipient, amount, reference)
    function _newImmediatePaymentCallData(address receiver, uint256 amount)
        private
        view
        returns (bytes memory)
    {
        return abi.encodeWithSelector(
            IFinance.newImmediatePayment.selector, address(ldo), receiver, amount, PAYMENT_REFERENCE
        );
    }

    /// @dev python: `needle.hex() in evm_script`
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

    function _addresses(address a) private pure returns (address[] memory addresses) {
        addresses = new address[](1);
        addresses[0] = a;
    }

    function _addresses(address a, address b) private pure returns (address[] memory addresses) {
        addresses = new address[](2);
        addresses[0] = a;
        addresses[1] = b;
    }

    function _addresses(address a, address b, address c)
        private
        pure
        returns (address[] memory addresses)
    {
        addresses = new address[](3);
        addresses[0] = a;
        addresses[1] = b;
        addresses[2] = c;
    }

    function _amounts(uint256 a) private pure returns (uint256[] memory amounts) {
        amounts = new uint256[](1);
        amounts[0] = a;
    }

    function _amounts(uint256 a, uint256 b) private pure returns (uint256[] memory amounts) {
        amounts = new uint256[](2);
        amounts[0] = a;
        amounts[1] = b;
    }
}
