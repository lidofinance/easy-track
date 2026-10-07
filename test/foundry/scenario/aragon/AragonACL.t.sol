// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IACL} from "test/foundry/interfaces/External.sol";

/// @notice The deployed Aragon ACL's parameterized permissions, which the node operator factories
///         build on: a grant with a parameter is invisible to the plain `hasPermission`, and a
///         regrant replaces the parameter list. The Agent manages a fresh role on itself.
contract AragonACLTest is EasyTrackScenarioBase {
    bytes32 private constant TEST_ROLE = keccak256("STAKING_MODULE_MANAGE_ROLE");

    /// @dev `Param(0, Op.EQ, value)`: the guarded call's first argument must equal `value`
    uint8 private constant FIRST_ARGUMENT = 0;
    uint8 private constant OP_EQ = 1;
    uint240 private constant PARAM_VALUE = 3;
    uint240 private constant NEW_PARAM_VALUE = 4;

    IACL internal acl;
    address internal agent;

    function setUp() public {
        _forkAndInitialize();

        acl = _acl();
        agent = config.agent;

        vm.label(address(acl), "ACL");
    }

    // python: test_aragon_acl_grant_role
    function testFork_CreatesPlainPermission() external {
        assertFalse(acl.hasPermission(stranger, agent, TEST_ROLE), "hasPermission before");

        vm.prank(agent);
        acl.createPermission(stranger, agent, TEST_ROLE, agent);

        assertTrue(acl.hasPermission(stranger, agent, TEST_ROLE), "hasPermission");
        assertEq(acl.getPermissionParamsLength(stranger, agent, TEST_ROLE), 0, "params length");
    }

    // python: test_aragon_acl_role_with_permission
    function testFork_GrantsRevokesAndRegrantsParameterizedPermission() external {
        assertFalse(acl.hasPermission(stranger, agent, TEST_ROLE), "hasPermission before");

        _createPermission();
        _grantPermissionWithParam(PARAM_VALUE);

        _assertPermissionParam(PARAM_VALUE);

        vm.prank(agent);
        acl.revokePermission(stranger, agent, TEST_ROLE);

        assertFalse(acl.hasPermission(stranger, agent, TEST_ROLE), "hasPermission after revoke");
        assertFalse(
            acl.hasPermission(stranger, agent, TEST_ROLE, _params(PARAM_VALUE)),
            "parameterized hasPermission after revoke"
        );
        assertEq(
            acl.getPermissionParamsLength(stranger, agent, TEST_ROLE),
            0,
            "params length after revoke"
        );

        // The revoked grant has no parameter list, so the ACL, at solc 0.4.24, halts on the index
        // with an invalid opcode and no data. The Brownie test checks a bare revert too.
        vm.expectRevert();
        acl.getPermissionParam(stranger, agent, TEST_ROLE, 0);

        _grantPermissionWithParam(NEW_PARAM_VALUE);

        _assertPermissionParam(NEW_PARAM_VALUE);
    }

    // python: test_aragon_acl_two_roles_with_different_params
    function testFork_RegrantReplacesPermissionParams() external {
        assertFalse(acl.hasPermission(stranger, agent, TEST_ROLE), "hasPermission before");

        _createPermission();
        _grantPermissionWithParam(PARAM_VALUE);

        _assertPermissionParam(PARAM_VALUE);

        _grantPermissionWithParam(NEW_PARAM_VALUE);

        _assertPermissionParam(NEW_PARAM_VALUE);
        assertFalse(
            acl.hasPermission(stranger, agent, TEST_ROLE, _params(PARAM_VALUE)),
            "hasPermission with the replaced param"
        );
    }

    /// @dev The Agent creates `TEST_ROLE` on itself, as its manager and first grantee
    function _createPermission() private {
        vm.prank(agent);
        acl.createPermission(agent, agent, TEST_ROLE, agent);
    }

    /// @dev Grant `stranger` the role with the single parameter `value`
    function _grantPermissionWithParam(uint240 value) private {
        vm.prank(agent);
        acl.grantPermissionP(stranger, agent, TEST_ROLE, _params(value));
    }

    /// @dev `encode_permission_params([Param(0, Op.EQ, value)])`, the parameter list of a grant
    ///      and the `how` of a parameterized `hasPermission`
    function _params(uint240 value) private pure returns (uint256[] memory params) {
        params = new uint256[](1);
        params[0] = (uint256(FIRST_ARGUMENT) << 248) | (uint256(OP_EQ) << 240) | value;
    }

    /// @dev `stranger` holds the role for the parameter `value` only, and that is its single one
    function _assertPermissionParam(uint240 value) private view {
        assertFalse(acl.hasPermission(stranger, agent, TEST_ROLE), "plain hasPermission");
        assertTrue(
            acl.hasPermission(stranger, agent, TEST_ROLE, _params(value)),
            "parameterized hasPermission"
        );
        assertEq(acl.getPermissionParamsLength(stranger, agent, TEST_ROLE), 1, "params length");

        (uint8 id, uint8 op, uint240 paramValue) =
            acl.getPermissionParam(stranger, agent, TEST_ROLE, 0);
        assertEq(id, FIRST_ARGUMENT, "param id");
        assertEq(op, OP_EQ, "param op");
        assertEq(paramValue, value, "param value");
    }
}
