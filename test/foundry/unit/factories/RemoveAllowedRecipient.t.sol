// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {RemoveAllowedRecipient} from "contracts/EVMScriptFactories/RemoveAllowedRecipient.sol";
import {AllowedRecipientsRegistry} from "contracts/AllowedRecipientsRegistry.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {
    BokkyPooBahsDateTimeContract
} from "test/foundry/unit/stubs/BokkyPooBahsDateTimeContract.sol";

contract RemoveAllowedRecipientTest is Test {
    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal addRecipientRoleHolder = makeAddr("addRecipientRoleHolder");
    address internal removeRecipientRoleHolder = makeAddr("removeRecipientRoleHolder");
    address internal setLimitRoleHolder = makeAddr("setLimitRoleHolder");
    address internal updateSpentRoleHolder = makeAddr("updateSpentRoleHolder");

    BokkyPooBahsDateTimeContract internal bokkyPooBahsDateTimeContract;
    AllowedRecipientsRegistry internal allowedRecipientsRegistry;
    RemoveAllowedRecipient internal removeAllowedRecipient;

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
        removeAllowedRecipient =
            new RemoveAllowedRecipient(owner, address(allowedRecipientsRegistry));
        vm.stopPrank();

        vm.label(address(bokkyPooBahsDateTimeContract), "bokkyPooBahsDateTimeContract");
        vm.label(address(allowedRecipientsRegistry), "allowedRecipientsRegistry");
        vm.label(address(removeAllowedRecipient), "removeAllowedRecipient");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(removeAllowedRecipient.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(removeAllowedRecipient.allowedRecipientsRegistry()),
            address(allowedRecipientsRegistry),
            "allowedRecipientsRegistry"
        );
    }

    // python: test_deploy_zero_trusted_caller
    function test_RevertWhen_TrustedCallerIsZeroAddress() external {
        vm.expectRevert("TRUSTED_CALLER_IS_ZERO_ADDRESS");
        new RemoveAllowedRecipient(address(0), address(allowedRecipientsRegistry));
    }

    // python: test_deploy_zero_allowed_recipient_registry
    function test_DeploysWithZeroAllowedRecipientsRegistry() external {
        vm.prank(owner);
        RemoveAllowedRecipient factory = new RemoveAllowedRecipient(owner, address(0));

        assertEq(
            address(factory.allowedRecipientsRegistry()), address(0), "allowedRecipientsRegistry"
        );
    }

    // python: test_create_evm_script_is_permissionless
    function test_CreateEVMScriptIsPermissionless() external {
        _allowStranger();

        vm.prank(stranger);
        bytes memory evmScript = removeAllowedRecipient.createEVMScript(owner, abi.encode(stranger));

        assertEq(evmScript, _removeRecipientScript(stranger), "evmScript");
    }

    // python: test_decode_evm_script_calldata_is_permissionless
    function test_DecodeEVMScriptCallDataIsPermissionless() external {
        vm.prank(stranger);
        address recipient = removeAllowedRecipient.decodeEVMScriptCallData(abi.encode(stranger));

        assertEq(recipient, stranger, "recipient");
    }

    // python: test_only_trusted_caller_can_be_creator
    function test_RevertWhen_CreatorIsNotTrustedCaller() external {
        _allowStranger();

        bytes memory callData = abi.encode(stranger);

        vm.prank(owner);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        removeAllowedRecipient.createEVMScript(stranger, callData);

        vm.prank(owner);
        bytes memory evmScript = removeAllowedRecipient.createEVMScript(owner, callData);

        assertEq(evmScript, _removeRecipientScript(stranger), "evmScript");
    }

    // python: test_revert_create_evm_script_with_empty_calldata
    function test_RevertWhen_CallDataIsEmpty() external {
        vm.expectRevert(bytes(""));
        removeAllowedRecipient.createEVMScript(owner, "");
    }

    // python: test_revert_recipient_not_found
    function test_RevertWhen_RecipientIsNotFound() external {
        vm.expectRevert("ALLOWED_RECIPIENT_NOT_FOUND");
        removeAllowedRecipient.createEVMScript(owner, abi.encode(stranger));
    }

    // python: test_create_evm_script_correctly
    function test_CreatesEVMScript() external {
        _allowStranger();

        bytes memory evmScript = removeAllowedRecipient.createEVMScript(owner, abi.encode(stranger));

        assertEq(evmScript, _removeRecipientScript(stranger), "evmScript");
    }

    // python: test_decode_evm_script_calldata_correctly
    function test_DecodesEVMScriptCallData() external view {
        address recipient = removeAllowedRecipient.decodeEVMScriptCallData(abi.encode(owner));

        assertEq(recipient, owner, "recipient");
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

    /// @dev python: encode_call_script of one registry.removeRecipient(recipient)
    function _removeRecipientScript(address recipient) private view returns (bytes memory) {
        return EVMScripts.encodeCallScript(
            address(allowedRecipientsRegistry),
            abi.encodeWithSelector(AllowedRecipientsRegistry.removeRecipient.selector, recipient)
        );
    }
}
