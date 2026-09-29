// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {EVMScriptPermissionsWrapper} from "contracts/test/EVMScriptPermissionsWrapper.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract EVMScriptPermissionsTest is Test {
    bytes internal constant ZERO_PERMISSION = hex"0000000000000000000000000000000000000000aabbccdd";
    bytes internal constant DEADBEEF_PERMISSION =
        hex"deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef";
    bytes internal constant FEEDFACE_PERMISSION =
        hex"feedfacefeedfacefeedfacefeedfacefeedfacebaddcafe";
    // ZERO_PERMISSION without its last byte, 23 bytes
    bytes internal constant ZERO_PERMISSION_TRUNCATED =
        hex"0000000000000000000000000000000000000000aabbcc";
    // ZERO_PERMISSION with one byte appended, 25 bytes
    bytes internal constant ZERO_PERMISSION_EXTENDED =
        hex"0000000000000000000000000000000000000000aabbccddee";

    address internal owner = makeAddr("owner");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal rewardAddress = makeAddr("rewardAddress");

    EVMScriptPermissionsWrapper internal wrapper;
    NodeOperatorsRegistryStub internal nodeOperatorsRegistryStub;

    function setUp() public {
        vm.startPrank(owner);
        wrapper = new EVMScriptPermissionsWrapper();
        nodeOperatorsRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);
        vm.stopPrank();
    }

    // python: test_can_execute_evm_script_zero_length_permissions
    function test_CannotExecuteEVMScriptWithZeroLengthPermissions() external view {
        assertFalse(wrapper.canExecuteEVMScript(hex"", hex""), "canExecuteEVMScript");
    }

    // python: test_can_execute_evm_script_wrong_permissions_length
    function test_CannotExecuteEVMScriptWithWrongPermissionsLength() external view {
        assertFalse(wrapper.canExecuteEVMScript(hex"0011223344", hex""), "canExecuteEVMScript");
    }

    // python: test_can_execute_evm_script_evm_script_too_short[0]
    function test_CannotExecuteTooShortEVMScriptWithZeroPermission() external view {
        assertFalse(wrapper.canExecuteEVMScript(ZERO_PERMISSION, hex""), "canExecuteEVMScript");
    }

    // python: test_can_execute_evm_script_evm_script_too_short[1]
    function test_CannotExecuteTooShortEVMScriptWithTripleZeroPermission() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(ZERO_PERMISSION, ZERO_PERMISSION, ZERO_PERMISSION),
                hex""
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_evm_script_too_short[2]
    function test_CannotExecuteTooShortEVMScriptWithDeadbeefPermission() external view {
        assertFalse(wrapper.canExecuteEVMScript(DEADBEEF_PERMISSION, hex""), "canExecuteEVMScript");
    }

    // python: test_can_execute_evm_script_evm_script_too_short[3]
    function test_CannotExecuteTooShortEVMScriptWithZeroAndDeadbeefPermissions() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION), hex""),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_evm_script_too_short[4]
    function test_CannotExecuteTooShortEVMScriptWithZeroDeadbeefAndFeedfacePermissions()
        external
        view
    {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION, FEEDFACE_PERMISSION),
                hex""
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_has_permissions[0] many_permissions_many_evm_scripts
    function test_CanExecuteEVMScriptWithManyPermissionsManyCalls() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(
                _allPermissions(),
                _script(_list(_setNodeOperatorStakingLimitCall(), _setRewardAddressCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_has_permissions[1] many_permissions_one_evm_script
    function test_CanExecuteEVMScriptWithManyPermissionsOneCall() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(_allPermissions(), _script(_list(_getNodeOperatorCall()))),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_has_permissions[2] one_permission_many_evm_scripts
    function test_CanExecuteEVMScriptWithOnePermissionManyCalls() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(
                _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                _script(_list(_getNodeOperatorCall(), _getNodeOperatorCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_has_permissions[3] one_permission_one_evm_script
    function test_CanExecuteEVMScriptWithOnePermissionOneCall() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(
                _permission(NodeOperatorsRegistryStub.setRewardAddress.selector),
                _script(_list(_setRewardAddressCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_has_no_permissions[0] has_all_except_one_permission
    function test_CannotExecuteEVMScriptMissingOnePermission() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(
                    _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                    _permission(NodeOperatorsRegistryStub.setRewardAddress.selector)
                ),
                _script(
                    _list(
                        _setNodeOperatorStakingLimitCall(),
                        _getNodeOperatorCall(),
                        _getNodeOperatorCall()
                    )
                )
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_has_no_permissions[1] has_no_required_permission_one_call
    function test_CannotExecuteEVMScriptWithoutRequiredPermissionOneCall() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(
                    _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                    _permission(NodeOperatorsRegistryStub.setRewardAddress.selector)
                ),
                _script(_list(_setNodeOperatorStakingLimitCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_can_execute_evm_script_has_no_permissions[2] has_no_required_permission_many_calls
    function test_CannotExecuteEVMScriptWithoutRequiredPermissionManyCalls() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                _script(_list(_setRewardAddressCall(), _setNodeOperatorStakingLimitCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    // python: test_is_valid_permissions_valid[0]
    function test_IsValidPermissionsZeroPermission() external view {
        assertTrue(wrapper.isValidPermissions(ZERO_PERMISSION), "isValidPermissions");
    }

    // python: test_is_valid_permissions_valid[1]
    function test_IsValidPermissionsTripleZeroPermission() external view {
        assertTrue(
            wrapper.isValidPermissions(
                bytes.concat(ZERO_PERMISSION, ZERO_PERMISSION, ZERO_PERMISSION)
            ),
            "isValidPermissions"
        );
    }

    // python: test_is_valid_permissions_valid[2]
    function test_IsValidPermissionsDeadbeefPermission() external view {
        assertTrue(wrapper.isValidPermissions(DEADBEEF_PERMISSION), "isValidPermissions");
    }

    // python: test_is_valid_permissions_valid[3]
    function test_IsValidPermissionsZeroAndDeadbeefPermissions() external view {
        assertTrue(
            wrapper.isValidPermissions(bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION)),
            "isValidPermissions"
        );
    }

    // python: test_is_valid_permissions_valid[4]
    function test_IsValidPermissionsZeroDeadbeefAndFeedfacePermissions() external view {
        assertTrue(
            wrapper.isValidPermissions(
                bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION, FEEDFACE_PERMISSION)
            ),
            "isValidPermissions"
        );
    }

    // python: test_is_valid_permissions_invalid[0]
    function test_IsInvalidPermissionsEmpty() external view {
        assertFalse(wrapper.isValidPermissions(hex""), "isValidPermissions");
    }

    // python: test_is_valid_permissions_invalid[1]
    function test_IsInvalidPermissionsTooShort() external view {
        assertFalse(wrapper.isValidPermissions(hex"11223344556677889911"), "isValidPermissions");
    }

    // python: test_is_valid_permissions_invalid[2]
    function test_IsInvalidPermissionsTruncated() external view {
        assertFalse(wrapper.isValidPermissions(ZERO_PERMISSION_TRUNCATED), "isValidPermissions");
    }

    // python: test_is_valid_permissions_invalid[3]
    function test_IsInvalidPermissionsExtended() external view {
        assertFalse(wrapper.isValidPermissions(ZERO_PERMISSION_EXTENDED), "isValidPermissions");
    }

    // python: test_is_valid_permissions_invalid[4]
    function test_IsInvalidPermissionsTripleTruncated() external view {
        assertFalse(
            wrapper.isValidPermissions(
                bytes.concat(ZERO_PERMISSION, ZERO_PERMISSION, ZERO_PERMISSION_TRUNCATED)
            ),
            "isValidPermissions"
        );
    }

    // python: create_permission on node_operators_registry_stub
    function _permission(bytes4 selector) private view returns (bytes memory) {
        return EVMScripts.createPermission(address(nodeOperatorsRegistryStub), selector);
    }

    // python: node_operators_registry_stub_permissions of all three methods
    function _allPermissions() private view returns (bytes memory) {
        return
            bytes.concat(
                _permission(NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector),
                _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                _permission(NodeOperatorsRegistryStub.setRewardAddress.selector)
            );
    }

    // python: node_operators_registry_stub_calldata
    function _script(bytes[] memory calls) private view returns (bytes memory) {
        address[] memory targets = new address[](calls.length);
        for (uint256 i; i < calls.length; ++i) {
            targets[i] = address(nodeOperatorsRegistryStub);
        }

        return EVMScripts.encodeCallScript(targets, calls);
    }

    function _setNodeOperatorStakingLimitCall() private pure returns (bytes memory) {
        return
            abi.encodeWithSelector(
                NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector,
                uint256(1),
                uint64(200)
            );
    }

    function _getNodeOperatorCall() private pure returns (bytes memory) {
        return
            abi.encodeWithSelector(
                NodeOperatorsRegistryStub.getNodeOperator.selector,
                uint256(1),
                false
            );
    }

    function _setRewardAddressCall() private view returns (bytes memory) {
        return
            abi.encodeWithSelector(
                NodeOperatorsRegistryStub.setRewardAddress.selector,
                rewardAddress
            );
    }

    function _list(bytes memory a) private pure returns (bytes[] memory list) {
        list = new bytes[](1);
        list[0] = a;
    }

    function _list(bytes memory a, bytes memory b) private pure returns (bytes[] memory list) {
        list = new bytes[](2);
        list[0] = a;
        list[1] = b;
    }

    function _list(
        bytes memory a,
        bytes memory b,
        bytes memory c
    ) private pure returns (bytes[] memory list) {
        list = new bytes[](3);
        list[0] = a;
        list[1] = b;
        list[2] = c;
    }
}
