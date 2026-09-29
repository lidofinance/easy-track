// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {EVMScriptFactoriesRegistry} from "contracts/EVMScriptFactoriesRegistry.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {TestHelpers} from "test/foundry/unit/helpers/TestHelpers.sol";

contract EVMScriptFactoriesRegistryTest is Test {
    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;

    /// @dev python: the "ffccddee" selector appended to the factory address
    bytes4 internal constant PERMISSION_SELECTOR = 0xffccddee;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    EVMScriptFactoriesRegistry internal evmScriptFactoriesRegistry;

    /// @dev python: permissions = stranger.address + "ffccddee"
    bytes internal permissions;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event EVMScriptFactoryAdded(address indexed _evmScriptFactory, bytes _permissions);
    event EVMScriptFactoryRemoved(address indexed _evmScriptFactory);

    function setUp() public {
        vm.prank(owner);
        evmScriptFactoriesRegistry = new EVMScriptFactoriesRegistry(owner);

        permissions = EVMScripts.createPermission(stranger, PERMISSION_SELECTOR);
    }

    // python: test_deploy
    function test_Deploy() external {
        vm.prank(owner);
        EVMScriptFactoriesRegistry newRegistry = new EVMScriptFactoriesRegistry(owner);

        assertTrue(
            newRegistry.hasRole(newRegistry.DEFAULT_ADMIN_ROLE(), owner),
            "DEFAULT_ADMIN_ROLE"
        );
    }

    // python: test_add_evm_script_factory_called_without_permissions
    function test_RevertWhen_AddingFactoryWithoutAdminRole() external {
        vm.prank(stranger);
        vm.expectRevert(TestHelpers.accessRevertMessage(stranger, DEFAULT_ADMIN_ROLE));
        evmScriptFactoriesRegistry.addEVMScriptFactory(stranger, permissions);
    }

    // python: test_add_evm_script_factory_empty_permissions
    function test_RevertWhen_AddingFactoryWithEmptyPermissions() external {
        vm.prank(owner);
        vm.expectRevert("INVALID_PERMISSIONS");
        evmScriptFactoriesRegistry.addEVMScriptFactory(stranger, "");
    }

    // python: test_add_evm_script_factory_invalid_length
    function test_RevertWhen_AddingFactoryWithInvalidPermissionsLength() external {
        // 5 bytes, not a multiple of the 24-byte address and selector pair
        vm.prank(owner);
        vm.expectRevert("INVALID_PERMISSIONS");
        evmScriptFactoriesRegistry.addEVMScriptFactory(stranger, hex"0011223344");
    }

    // python: test_add_evm_script
    function test_AddsEVMScriptFactory() external {
        vm.expectEmit(address(evmScriptFactoriesRegistry));
        emit EVMScriptFactoryAdded(stranger, permissions);

        vm.prank(owner);
        evmScriptFactoriesRegistry.addEVMScriptFactory(stranger, permissions);
    }

    // python: test_add_evm_script_twice
    function test_RevertWhen_AddingFactoryTwice() external {
        vm.prank(owner);
        evmScriptFactoriesRegistry.addEVMScriptFactory(stranger, permissions);

        vm.prank(owner);
        vm.expectRevert("EVM_SCRIPT_FACTORY_ALREADY_ADDED");
        evmScriptFactoriesRegistry.addEVMScriptFactory(stranger, permissions);
    }

    // python: test_remove_evm_script_factory_not_found
    function test_RevertWhen_RemovingUnknownFactory() external {
        vm.prank(owner);
        vm.expectRevert("EVM_SCRIPT_FACTORY_NOT_FOUND");
        evmScriptFactoriesRegistry.removeEVMScriptFactory(stranger);
    }

    // python: test_remove_evm_script_factory
    function test_RemovesEVMScriptFactory() external {
        address[] memory evmScriptFactories = _extraEVMScriptFactories();

        vm.startPrank(owner);
        for (uint256 i; i < evmScriptFactories.length; ++i) {
            evmScriptFactoriesRegistry.addEVMScriptFactory(evmScriptFactories[i], permissions);
        }

        vm.stopPrank();

        // python: removing_order, indices into the shrinking local list. Swap-and-pop order:
        // [0,1,2,(3),4] -> [0,1,2,4], [0,(1),2,4] -> [0,4,2], [(0),4,2] -> [2,4],
        // [2,(4)] -> [2], [(2)] -> []
        uint256[5] memory removingOrder = [uint256(3), 1, 0, 1, 0];

        for (uint256 i; i < removingOrder.length; ++i) {
            address toRemove = evmScriptFactories[removingOrder[i]];
            evmScriptFactories = _pop(evmScriptFactories, removingOrder[i]);

            assertTrue(
                evmScriptFactoriesRegistry.isEVMScriptFactory(toRemove),
                "isEVMScriptFactory"
            );

            vm.expectEmit(address(evmScriptFactoriesRegistry));
            emit EVMScriptFactoryRemoved(toRemove);

            vm.recordLogs();

            vm.prank(owner);
            evmScriptFactoriesRegistry.removeEVMScriptFactory(toRemove);

            assertFalse(
                evmScriptFactoriesRegistry.isEVMScriptFactory(toRemove),
                "isEVMScriptFactory"
            );
            assertEq(vm.getRecordedLogs().length, 1, "events");
            assertEq(
                evmScriptFactoriesRegistry.getEVMScriptFactories().length,
                evmScriptFactories.length,
                "evmScriptFactories.length"
            );
        }
    }

    /// @dev python: extra_evm_script_factories = accounts[3:8], plain accounts registered as factories
    function _extraEVMScriptFactories() private returns (address[] memory evmScriptFactories) {
        evmScriptFactories = new address[](5);
        evmScriptFactories[0] = makeAddr("evmScriptFactory1");
        evmScriptFactories[1] = makeAddr("evmScriptFactory2");
        evmScriptFactories[2] = makeAddr("evmScriptFactory3");
        evmScriptFactories[3] = makeAddr("evmScriptFactory4");
        evmScriptFactories[4] = makeAddr("evmScriptFactory5");
    }

    /// @dev python: list.pop(index). Drops the element at `index` and keeps the order of the rest
    function _pop(address[] memory list, uint256 index)
        private
        pure
        returns (address[] memory result)
    {
        result = new address[](list.length - 1);

        for (uint256 i; i < index; ++i) {
            result[i] = list[i];
        }

        for (uint256 i = index + 1; i < list.length; ++i) {
            result[i - 1] = list[i];
        }
    }
}
