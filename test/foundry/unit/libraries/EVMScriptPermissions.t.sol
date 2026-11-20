// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {EVMScriptPermissionsWrapper} from "contracts/test/EVMScriptPermissionsWrapper.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
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

    function test_ForbidsEVMScriptWithZeroLengthPermissions() external view {
        assertFalse(wrapper.canExecuteEVMScript(hex"", hex""), "canExecuteEVMScript");
    }

    function test_ForbidsEVMScriptWithWrongPermissionsLength() external view {
        assertFalse(wrapper.canExecuteEVMScript(hex"0011223344", hex""), "canExecuteEVMScript");
    }

    function test_ForbidsTooShortEVMScriptWithZeroPermission() external view {
        assertFalse(wrapper.canExecuteEVMScript(ZERO_PERMISSION, hex""), "canExecuteEVMScript");
    }

    function test_ForbidsTooShortEVMScriptWithTripleZeroPermission() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(ZERO_PERMISSION, ZERO_PERMISSION, ZERO_PERMISSION), hex""
            ),
            "canExecuteEVMScript"
        );
    }

    function test_ForbidsTooShortEVMScriptWithDeadbeefPermission() external view {
        assertFalse(wrapper.canExecuteEVMScript(DEADBEEF_PERMISSION, hex""), "canExecuteEVMScript");
    }

    function test_ForbidsTooShortEVMScriptWithZeroAndDeadbeefPermissions() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION), hex""),
            "canExecuteEVMScript"
        );
    }

    function test_ForbidsTooShortEVMScriptWithZeroDeadbeefAndFeedfacePermissions() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION, FEEDFACE_PERMISSION), hex""
            ),
            "canExecuteEVMScript"
        );
    }

    function test_AllowsEVMScriptWithManyPermissionsManyCalls() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(
                _allPermissions(),
                _script(Arrays.list(_setNodeOperatorStakingLimitCall(), _setRewardAddressCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    function test_AllowsEVMScriptWithManyPermissionsOneCall() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(
                _allPermissions(), _script(Arrays.list(_getNodeOperatorCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    function test_AllowsEVMScriptWithOnePermissionManyCalls() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(
                _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                _script(Arrays.list(_getNodeOperatorCall(), _getNodeOperatorCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    function test_AllowsEVMScriptWithOnePermissionOneCall() external view {
        assertTrue(
            wrapper.canExecuteEVMScript(
                _permission(NodeOperatorsRegistryStub.setRewardAddress.selector),
                _script(Arrays.list(_setRewardAddressCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    function test_ForbidsEVMScriptMissingOnePermission() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(
                    _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                    _permission(NodeOperatorsRegistryStub.setRewardAddress.selector)
                ),
                _script(
                    Arrays.list(
                        _setNodeOperatorStakingLimitCall(),
                        _getNodeOperatorCall(),
                        _getNodeOperatorCall()
                    )
                )
            ),
            "canExecuteEVMScript"
        );
    }

    function test_ForbidsEVMScriptWithoutRequiredPermissionOneCall() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                bytes.concat(
                    _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                    _permission(NodeOperatorsRegistryStub.setRewardAddress.selector)
                ),
                _script(Arrays.list(_setNodeOperatorStakingLimitCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    function test_ForbidsEVMScriptWithoutRequiredPermissionManyCalls() external view {
        assertFalse(
            wrapper.canExecuteEVMScript(
                _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
                _script(Arrays.list(_setRewardAddressCall(), _setNodeOperatorStakingLimitCall()))
            ),
            "canExecuteEVMScript"
        );
    }

    function test_AcceptsZeroPermission() external view {
        assertTrue(wrapper.isValidPermissions(ZERO_PERMISSION), "isValidPermissions");
    }

    function test_AcceptsTripleZeroPermission() external view {
        assertTrue(
            wrapper.isValidPermissions(
                bytes.concat(ZERO_PERMISSION, ZERO_PERMISSION, ZERO_PERMISSION)
            ),
            "isValidPermissions"
        );
    }

    function test_AcceptsDeadbeefPermission() external view {
        assertTrue(wrapper.isValidPermissions(DEADBEEF_PERMISSION), "isValidPermissions");
    }

    function test_AcceptsZeroAndDeadbeefPermissions() external view {
        assertTrue(
            wrapper.isValidPermissions(bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION)),
            "isValidPermissions"
        );
    }

    function test_AcceptsZeroDeadbeefAndFeedfacePermissions() external view {
        assertTrue(
            wrapper.isValidPermissions(
                bytes.concat(ZERO_PERMISSION, DEADBEEF_PERMISSION, FEEDFACE_PERMISSION)
            ),
            "isValidPermissions"
        );
    }

    function test_RejectsEmptyPermissions() external view {
        assertFalse(wrapper.isValidPermissions(hex""), "isValidPermissions");
    }

    function test_RejectsTooShortPermissions() external view {
        assertFalse(wrapper.isValidPermissions(hex"11223344556677889911"), "isValidPermissions");
    }

    function test_RejectsTruncatedPermissions() external view {
        assertFalse(wrapper.isValidPermissions(ZERO_PERMISSION_TRUNCATED), "isValidPermissions");
    }

    function test_RejectsExtendedPermissions() external view {
        assertFalse(wrapper.isValidPermissions(ZERO_PERMISSION_EXTENDED), "isValidPermissions");
    }

    function test_RejectsTripleTruncatedPermissions() external view {
        assertFalse(
            wrapper.isValidPermissions(
                bytes.concat(ZERO_PERMISSION, ZERO_PERMISSION, ZERO_PERMISSION_TRUNCATED)
            ),
            "isValidPermissions"
        );
    }

    function _permission(bytes4 selector) private view returns (bytes memory) {
        return EVMScripts.createPermission(address(nodeOperatorsRegistryStub), selector);
    }

    function _allPermissions() private view returns (bytes memory) {
        return bytes.concat(
            _permission(NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector),
            _permission(NodeOperatorsRegistryStub.getNodeOperator.selector),
            _permission(NodeOperatorsRegistryStub.setRewardAddress.selector)
        );
    }

    function _script(bytes[] memory calls) private view returns (bytes memory) {
        address[] memory targets = new address[](calls.length);
        for (uint256 i; i < calls.length; ++i) {
            targets[i] = address(nodeOperatorsRegistryStub);
        }

        return EVMScripts.encodeCallScript(targets, calls);
    }

    function _setNodeOperatorStakingLimitCall() private pure returns (bytes memory) {
        return abi.encodeWithSelector(
            NodeOperatorsRegistryStub.setNodeOperatorStakingLimit.selector, uint256(1), uint64(200)
        );
    }

    function _getNodeOperatorCall() private pure returns (bytes memory) {
        return abi.encodeWithSelector(
            NodeOperatorsRegistryStub.getNodeOperator.selector, uint256(1), false
        );
    }

    function _setRewardAddressCall() private view returns (bytes memory) {
        return
            abi.encodeWithSelector(
                NodeOperatorsRegistryStub.setRewardAddress.selector, rewardAddress
            );
    }
}
