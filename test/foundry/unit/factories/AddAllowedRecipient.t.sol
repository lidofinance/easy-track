// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AddAllowedRecipient} from "contracts/EVMScriptFactories/AddAllowedRecipient.sol";
import {AllowedRecipientsRegistry} from "contracts/AllowedRecipientsRegistry.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {
    BokkyPooBahsDateTimeContract
} from "test/foundry/unit/stubs/BokkyPooBahsDateTimeContract.sol";

contract AddAllowedRecipientTest is Test {
    string internal constant EVM_SCRIPT_CALLDATA_TITLE = "TITLE";

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal addRecipientRoleHolder = makeAddr("addRecipientRoleHolder");
    address internal removeRecipientRoleHolder = makeAddr("removeRecipientRoleHolder");
    address internal setLimitRoleHolder = makeAddr("setLimitRoleHolder");
    address internal updateSpentRoleHolder = makeAddr("updateSpentRoleHolder");

    BokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;
    AllowedRecipientsRegistry internal allowedRecipientsRegistry;
    AddAllowedRecipient internal addAllowedRecipient;

    function setUp() public {
        bokkyPooBahsDateTimeContract = new BokkyPooBahsDateTimeContract();

        vm.startPrank(owner);
        allowedRecipientsRegistry = new AllowedRecipientsRegistry(
            owner,
            _holders(addRecipientRoleHolder),
            _holders(removeRecipientRoleHolder),
            _holders(setLimitRoleHolder),
            _holders(updateSpentRoleHolder),
            bokkyPooBahsDateTimeContract
        );
        addAllowedRecipient = new AddAllowedRecipient(owner, address(allowedRecipientsRegistry));
        vm.stopPrank();

        vm.label(address(bokkyPooBahsDateTimeContract), "bokkyPooBahsDateTimeContract");
        vm.label(address(allowedRecipientsRegistry), "allowedRecipientsRegistry");
        vm.label(address(addAllowedRecipient), "addAllowedRecipient");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(addAllowedRecipient.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(addAllowedRecipient.allowedRecipientsRegistry()),
            address(allowedRecipientsRegistry),
            "allowedRecipientsRegistry"
        );
    }

    // python: test_deploy_zero_trusted_caller
    function test_RevertWhen_TrustedCallerIsZeroAddress() external {
        vm.expectRevert("TRUSTED_CALLER_IS_ZERO_ADDRESS");
        new AddAllowedRecipient(address(0), address(allowedRecipientsRegistry));
    }

    // python: test_deploy_zero_allowed_recipient_registry
    function test_DeploysWithZeroAllowedRecipientsRegistry() external {
        vm.prank(owner);
        AddAllowedRecipient factory = new AddAllowedRecipient(owner, address(0));

        assertEq(
            address(factory.allowedRecipientsRegistry()), address(0), "allowedRecipientsRegistry"
        );
    }

    // python: test_create_evm_script_is_permissionless
    function test_CreateEVMScriptIsPermissionless() external {
        vm.prank(stranger);
        bytes memory evmScript = addAllowedRecipient.createEVMScript(owner, _callData(owner));

        assertEq(evmScript, _addRecipientScript(owner), "evmScript");
    }

    // python: test_decode_evm_script_calldata_is_permissionless
    function test_DecodeEVMScriptCallDataIsPermissionless() external {
        vm.prank(stranger);
        (address recipient, string memory title) =
            addAllowedRecipient.decodeEVMScriptCallData(_callData(stranger));

        assertEq(recipient, stranger, "recipient");
        assertEq(title, EVM_SCRIPT_CALLDATA_TITLE, "title");
    }

    // python: test_only_trusted_caller_can_be_creator
    function test_RevertWhen_CreatorIsNotTrustedCaller() external {
        bytes memory callData = _callData(owner);

        vm.prank(owner);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        addAllowedRecipient.createEVMScript(stranger, callData);

        vm.prank(owner);
        bytes memory evmScript = addAllowedRecipient.createEVMScript(owner, callData);

        assertEq(evmScript, _addRecipientScript(owner), "evmScript");
    }

    // python: test_revert_create_evm_script_with_empty_calldata
    function test_RevertWhen_CallDataIsEmpty() external {
        vm.expectRevert(bytes(""));
        addAllowedRecipient.createEVMScript(owner, "");
    }

    // python: test_revert_create_evm_script_with_empty_recipient_address
    function test_RevertWhen_RecipientAddressIsZero() external {
        vm.expectRevert("RECIPIENT_ADDRESS_IS_ZERO_ADDRESS");
        addAllowedRecipient.createEVMScript(owner, _callData(address(0)));
    }

    // python: test_revert_recipient_already_added
    function test_RevertWhen_RecipientIsAlreadyAdded() external {
        _allowStranger();

        vm.expectRevert("ALLOWED_RECIPIENT_ALREADY_ADDED");
        addAllowedRecipient.createEVMScript(owner, _callData(stranger));
    }

    // python: test_create_evm_script_correctly
    function test_CreatesEVMScript() external view {
        bytes memory evmScript = addAllowedRecipient.createEVMScript(owner, _callData(owner));

        assertEq(evmScript, _addRecipientScript(owner), "evmScript");
    }

    // python: test_decode_evm_script_calldata_correctly
    function test_DecodesEVMScriptCallData() external view {
        (address recipient, string memory title) =
            addAllowedRecipient.decodeEVMScriptCallData(_callData(owner));

        assertEq(recipient, owner, "recipient");
        assertEq(title, EVM_SCRIPT_CALLDATA_TITLE, "title");
    }

    function _holders(address holder) private pure returns (address[] memory holders) {
        holders = new address[](1);
        holders[0] = holder;
    }

    /// @dev python: registry.addRecipient(stranger, "Stranger") from add_recipient_role_holder
    function _allowStranger() private {
        vm.prank(addRecipientRoleHolder);
        allowedRecipientsRegistry.addRecipient(stranger, "Stranger");
    }

    /// @dev python: encode_calldata(["address", "string"], [recipient, "TITLE"])
    function _callData(address recipient) private pure returns (bytes memory) {
        return abi.encode(recipient, EVM_SCRIPT_CALLDATA_TITLE);
    }

    /// @dev python: encode_call_script of one registry.addRecipient(recipient, "TITLE")
    function _addRecipientScript(address recipient) private view returns (bytes memory) {
        return EVMScripts.encodeCallScript(
            address(allowedRecipientsRegistry),
            abi.encodeWithSelector(
                AllowedRecipientsRegistry.addRecipient.selector,
                recipient,
                EVM_SCRIPT_CALLDATA_TITLE
            )
        );
    }
}
