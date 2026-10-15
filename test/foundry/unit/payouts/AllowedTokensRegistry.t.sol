// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {AllowedTokensRegistry} from "contracts/payouts/multi-token/AllowedTokensRegistry.sol";
import {MockERC20} from "contracts/test/MockERC20.sol";
import {TestHelpers} from "test/foundry/unit/helpers/TestHelpers.sol";

contract AllowedTokensRegistryTest is Test {
    // python: utils/test_helpers.py role constants
    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 internal constant ADD_TOKEN_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_TOKEN_TO_ALLOWED_LIST_ROLE");
    bytes32 internal constant REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE");

    /// @dev python: accounts[0:20], the sweep of test_multiple_role_holders
    uint256 internal constant ACCOUNTS_COUNT = 20;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal voting = makeAddr("voting");
    address internal ldo = makeAddr("ldo");
    address internal steth = makeAddr("steth");
    address internal addTokenRoleHolder = makeAddr("addTokenRoleHolder");
    address internal removeTokenRoleHolder = makeAddr("removeTokenRoleHolder");

    AllowedTokensRegistry internal allowedTokensRegistry;

    function setUp() public {
        vm.prank(owner);
        allowedTokensRegistry = new AllowedTokensRegistry(
            owner, _holders(addTokenRoleHolder), _holders(removeTokenRoleHolder)
        );

        vm.label(address(allowedTokensRegistry), "allowedTokensRegistry");
    }

    // python: test_registry_initial_state
    function test_RegistryInitialState() external {
        vm.prank(owner);
        AllowedTokensRegistry registry = new AllowedTokensRegistry(
            owner, _holders(addTokenRoleHolder), _holders(removeTokenRoleHolder)
        );

        assertTrue(registry.hasRole(DEFAULT_ADMIN_ROLE, owner), "owner DEFAULT_ADMIN_ROLE");
        assertTrue(
            registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, addTokenRoleHolder),
            "addTokenRoleHolder ADD_TOKEN_TO_ALLOWED_LIST_ROLE"
        );
        assertTrue(
            registry.hasRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, removeTokenRoleHolder),
            "removeTokenRoleHolder REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE"
        );
        assertFalse(
            registry.hasRole(DEFAULT_ADMIN_ROLE, addTokenRoleHolder),
            "addTokenRoleHolder DEFAULT_ADMIN_ROLE"
        );
        assertFalse(
            registry.hasRole(DEFAULT_ADMIN_ROLE, removeTokenRoleHolder),
            "removeTokenRoleHolder DEFAULT_ADMIN_ROLE"
        );
        assertEq(registry.getAllowedTokens().length, 0, "getAllowedTokens().length");
    }

    // python: test_registry_zero_admin_allowed
    function test_RegistryZeroAdminAllowed() external {
        vm.prank(owner);
        AllowedTokensRegistry registry =
            new AllowedTokensRegistry(address(0), _holders(owner), _holders(owner));

        assertTrue(
            registry.hasRole(DEFAULT_ADMIN_ROLE, address(0)), "zero admin DEFAULT_ADMIN_ROLE"
        );
    }

    // python: test_registry_none_role_holders_allowed
    function test_RegistryNoneRoleHoldersAllowed() external {
        vm.prank(owner);
        AllowedTokensRegistry registry =
            new AllowedTokensRegistry(owner, new address[](0), new address[](0));

        assertTrue(registry.hasRole(DEFAULT_ADMIN_ROLE, owner), "owner DEFAULT_ADMIN_ROLE");
    }

    // python: test_rights_are_not_shared_by_different_roles
    function test_RightsAreNotSharedByDifferentRoles() external {
        vm.prank(owner);
        AllowedTokensRegistry registry = new AllowedTokensRegistry(
            voting, _holders(addTokenRoleHolder), _holders(removeTokenRoleHolder)
        );

        assertTrue(registry.hasRole(DEFAULT_ADMIN_ROLE, voting), "voting DEFAULT_ADMIN_ROLE");

        address[3] memory addForbidden = [owner, removeTokenRoleHolder, stranger];

        for (uint256 i; i < addForbidden.length; ++i) {
            vm.prank(addForbidden[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(addForbidden[i], ADD_TOKEN_TO_ALLOWED_LIST_ROLE)
            );
            registry.addToken(ldo);
        }

        address[3] memory removeForbidden = [owner, addTokenRoleHolder, stranger];

        for (uint256 i; i < removeForbidden.length; ++i) {
            vm.prank(removeForbidden[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(
                    removeForbidden[i], REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE
                )
            );
            registry.removeToken(ldo);
        }
    }

    // python: test_multiple_role_holders
    function test_MultipleRoleHolders() external {
        address[] memory accounts = _accounts();
        address[] memory addTokenRoleHolders = _holders(accounts[2], accounts[3]);
        address[] memory removeTokenRoleHolders = _holders(accounts[4], accounts[5]);

        vm.prank(owner);
        AllowedTokensRegistry registry =
            new AllowedTokensRegistry(voting, addTokenRoleHolders, removeTokenRoleHolders);

        address[] memory addForbidden = _without(accounts, addTokenRoleHolders);

        for (uint256 i; i < addForbidden.length; ++i) {
            vm.prank(addForbidden[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(addForbidden[i], ADD_TOKEN_TO_ALLOWED_LIST_ROLE)
            );
            registry.addToken(ldo);
        }

        vm.prank(addTokenRoleHolders[0]);
        registry.addToken(ldo);

        vm.prank(addTokenRoleHolders[1]);
        registry.addToken(steth);

        assertTrue(registry.isTokenAllowed(ldo), "ldo allowed");
        assertTrue(registry.isTokenAllowed(steth), "steth allowed");

        address[] memory removeForbidden = _without(accounts, removeTokenRoleHolders);

        for (uint256 i; i < removeForbidden.length; ++i) {
            vm.prank(removeForbidden[i]);
            vm.expectRevert(
                TestHelpers.accessRevertMessage(
                    removeForbidden[i], REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE
                )
            );
            registry.removeToken(ldo);
        }

        vm.prank(removeTokenRoleHolders[0]);
        registry.removeToken(ldo);

        vm.prank(removeTokenRoleHolders[1]);
        registry.removeToken(steth);

        assertEq(registry.getAllowedTokens().length, 0, "getAllowedTokens().length");
    }

    // python: test_add_tokens
    function test_AddsToken() external {
        vm.prank(addTokenRoleHolder);
        allowedTokensRegistry.addToken(ldo);

        assertTrue(allowedTokensRegistry.isTokenAllowed(ldo), "isTokenAllowed");
        assertEq(allowedTokensRegistry.getAllowedTokens(), _holders(ldo), "getAllowedTokens");
    }

    // python: test_add_multiple_tokens
    function test_AddsMultipleTokens() external {
        vm.startPrank(addTokenRoleHolder);
        allowedTokensRegistry.addToken(ldo);
        allowedTokensRegistry.addToken(steth);
        vm.stopPrank();

        assertTrue(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed");
        assertTrue(allowedTokensRegistry.isTokenAllowed(steth), "steth allowed");
        assertEq(allowedTokensRegistry.getAllowedTokens(), _holders(ldo, steth), "getAllowedTokens");
    }

    // python: test_add_zero_token
    function test_RevertWhen_TokenIsZeroAddress() external {
        vm.prank(addTokenRoleHolder);
        vm.expectRevert("TOKEN_ADDRESS_IS_ZERO");
        allowedTokensRegistry.addToken(address(0));
    }

    // python: test_add_the_same_token
    function test_RevertWhen_TokenIsAlreadyAdded() external {
        _allowToken(ldo);

        vm.prank(addTokenRoleHolder);
        vm.expectRevert("TOKEN_ALREADY_ADDED_TO_ALLOWED_LIST");
        allowedTokensRegistry.addToken(ldo);
    }

    // python: test_remove_token
    function test_RemovesToken() external {
        _allowToken(ldo);

        assertTrue(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed before");
        assertEq(allowedTokensRegistry.getAllowedTokens().length, 1, "length before");

        vm.prank(removeTokenRoleHolder);
        allowedTokensRegistry.removeToken(ldo);

        assertFalse(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed after");
        assertEq(allowedTokensRegistry.getAllowedTokens().length, 0, "length after");
    }

    // python: test_remove_multiple_tokens
    function test_RemovesMultipleTokens() external {
        _allowToken(ldo);
        _allowToken(steth);

        assertTrue(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed before");
        assertTrue(allowedTokensRegistry.isTokenAllowed(steth), "steth allowed before");
        assertEq(allowedTokensRegistry.getAllowedTokens().length, 2, "length before");

        vm.prank(removeTokenRoleHolder);
        allowedTokensRegistry.removeToken(ldo);

        assertFalse(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed after first removal");
        assertTrue(allowedTokensRegistry.isTokenAllowed(steth), "steth allowed after first removal");
        assertEq(allowedTokensRegistry.getAllowedTokens().length, 1, "length after first removal");

        vm.prank(removeTokenRoleHolder);
        allowedTokensRegistry.removeToken(steth);

        assertFalse(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed after second removal");
        assertFalse(
            allowedTokensRegistry.isTokenAllowed(steth), "steth allowed after second removal"
        );
        assertEq(allowedTokensRegistry.getAllowedTokens().length, 0, "length after second removal");
    }

    // python: test_remove_the_same_token
    function test_RevertWhen_TokenIsRemovedTwice() external {
        _allowToken(ldo);

        assertTrue(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed before");
        assertEq(allowedTokensRegistry.getAllowedTokens().length, 1, "length before");

        vm.prank(removeTokenRoleHolder);
        allowedTokensRegistry.removeToken(ldo);

        assertFalse(allowedTokensRegistry.isTokenAllowed(ldo), "ldo allowed after");
        assertEq(allowedTokensRegistry.getAllowedTokens().length, 0, "length after");

        vm.prank(removeTokenRoleHolder);
        vm.expectRevert("TOKEN_NOT_FOUND_IN_ALLOWED_LIST");
        allowedTokensRegistry.removeToken(ldo);
    }

    // python: test_remove_not_existing_token
    function test_RevertWhen_TokenIsNotFound() external {
        vm.prank(removeTokenRoleHolder);
        vm.expectRevert("TOKEN_NOT_FOUND_IN_ALLOWED_LIST");
        allowedTokensRegistry.removeToken(ldo);
    }

    // python: test_normalize_amount
    function test_NormalizesAmount() external {
        vm.expectRevert("TOKEN_ADDRESS_IS_ZERO");
        allowedTokensRegistry.normalizeAmount(1, address(0));

        vm.prank(owner);
        MockERC20 erc20Decimals18 = new MockERC20(18);
        uint256 preciseAmount = 1000000000000000999;

        assertEq(
            allowedTokensRegistry.normalizeAmount(preciseAmount, address(erc20Decimals18)),
            preciseAmount,
            "18 decimals"
        );

        vm.prank(owner);
        MockERC20 erc20Decimals21 = new MockERC20(21);
        uint256 amountWith21Decimals = 1000000000000000999000;

        assertEq(
            allowedTokensRegistry.normalizeAmount(amountWith21Decimals, address(erc20Decimals21)),
            preciseAmount,
            "21 decimals"
        );
        assertEq(
            allowedTokensRegistry.normalizeAmount(
                amountWith21Decimals + 1, address(erc20Decimals21)
            ),
            preciseAmount + 1,
            "21 decimals rounded up"
        );

        vm.prank(owner);
        MockERC20 erc20Decimals12 = new MockERC20(12);

        assertEq(
            allowedTokensRegistry.normalizeAmount(1000000000009, address(erc20Decimals12)),
            1000000000009000000,
            "12 decimals"
        );
    }

    /// @dev python: registry.addToken(token) from add_token_role_holder
    function _allowToken(address token) private {
        vm.prank(addTokenRoleHolder);
        allowedTokensRegistry.addToken(token);
    }

    function _holders(address holder) private pure returns (address[] memory holders) {
        holders = new address[](1);
        holders[0] = holder;
    }

    function _holders(address first, address second)
        private
        pure
        returns (address[] memory holders)
    {
        holders = new address[](2);
        holders[0] = first;
        holders[1] = second;
    }

    /// @dev python: accounts[0:20]
    function _accounts() private returns (address[] memory accounts) {
        accounts = new address[](ACCOUNTS_COUNT);

        for (uint256 i; i < ACCOUNTS_COUNT; ++i) {
            accounts[i] = makeAddr(string(abi.encodePacked("account", vm.toString(i))));
        }
    }

    /// @dev python: `caller for caller in accounts if caller not in holders`
    function _without(address[] memory accounts, address[] memory excluded)
        private
        pure
        returns (address[] memory rest)
    {
        rest = new address[](accounts.length - excluded.length);
        uint256 count;

        for (uint256 i; i < accounts.length; ++i) {
            if (!_contains(excluded, accounts[i])) {
                rest[count++] = accounts[i];
            }
        }
    }

    function _contains(address[] memory list, address item) private pure returns (bool) {
        for (uint256 i; i < list.length; ++i) {
            if (list[i] == item) return true;
        }

        return false;
    }
}
