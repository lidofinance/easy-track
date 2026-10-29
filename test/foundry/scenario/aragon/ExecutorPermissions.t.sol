// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {GrantExecutorPermissions} from "script/GrantExecutorPermissions.s.sol";
import {RevokeAllPermissions} from "script/RevokeAllPermissions.s.sol";
import {Lido} from "script/helpers/Lido.sol";
import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IACL, ILidoLocator, IMiniMeToken} from "test/foundry/interfaces/External.sol";

/// @notice `script/GrantExecutorPermissions.s.sol` and `script/RevokeAllPermissions.s.sol` run
///         on the fork for a fresh executor, their votes passed with minted LDO and executed:
///         the grant of `CREATE_PAYMENTS_ROLE` on Finance and `SET_NODE_OPERATOR_LIMIT_ROLE` on
///         the curated registry, then their revocation, after which the executor holds no
///         permission of the six DAO apps. A setup vote first hands Voting the manager slot of
///         each required role, so its votes may touch them.
contract ExecutorPermissionsTest is EasyTrackScenarioBase {
    Lido.DAO internal dao;
    IACL internal acl;
    GrantExecutorPermissions internal grant;
    RevokeAllPermissions internal revoke;

    function setUp() public {
        _forkAndInitialize();

        dao = Lido.dao();
        acl = Lido.acl(dao);
        grant = new GrantExecutorPermissions();
        revoke = new RevokeAllPermissions();

        vm.label(address(acl), "ACL");
        vm.label(dao.voting, "Voting");
        vm.label(dao.finance, "Finance");
        vm.label(dao.tokenManager, "TokenManager");
        vm.label(ILidoLocator(dao.locator).lido(), "Lido");
        vm.label(Lido.curatedRegistry(dao), "NodeOperatorsRegistry");
        vm.label(address(grant), "GrantExecutorPermissions");
        vm.label(address(revoke), "RevokeAllPermissions");

        _deployEasyTrack(address(this));
        _handPermissionManagerToVoting(Lido.executorPermissions(dao));

        // The scripts hold LDO to forward through the TokenManager, the test enough to pass a
        // vote alone
        _mintLDO(address(grant), 1 ether);
        _mintLDO(address(revoke), 1 ether);
        _mintLDO(address(this), IMiniMeToken(dao.ldo).totalSupply());
    }

    function testFork_GrantsExecutorPermissions() external {
        Lido.Permission[] memory required = Lido.executorPermissions(dao);

        _assertPermissions(required, false);
        assertEq(grant.missingPermissions(evmScriptExecutor).length, required.length, "missing");

        uint256 voteId =
            grant.createVote(evmScriptExecutor, grant.missingPermissions(evmScriptExecutor));

        _voteAndExecute(voteId);

        _assertPermissions(required, true);
        assertEq(grant.missingPermissions(evmScriptExecutor).length, 0, "missing after");
    }

    function testFork_RevokesAllPermissions() external {
        Lido.Permission[] memory required = Lido.executorPermissions(dao);

        _voteAndExecute(grant.createVote(evmScriptExecutor, required));

        _assertPermissions(required, true);
        assertEq(revoke.grantedPermissions(evmScriptExecutor).length, required.length, "granted");

        uint256 voteId =
            revoke.createVote(evmScriptExecutor, revoke.grantedPermissions(evmScriptExecutor));

        _voteAndExecute(voteId);

        _assertPermissions(Lido.allPermissions(dao), false);
        assertEq(revoke.grantedPermissions(evmScriptExecutor).length, 0, "granted after");
    }

    /// @dev The setup vote "Grant permission manager to Voting", for each role Voting does not
    ///      manage yet
    function _handPermissionManagerToVoting(Lido.Permission[] memory permissions) private {
        for (uint256 i; i < permissions.length; ++i) {
            address app = permissions[i].app;
            bytes32 role = Lido.roleId(permissions[i]);
            address manager = acl.getPermissionManager(app, role);
            if (manager == dao.voting) continue;

            vm.prank(manager);
            acl.setPermissionManager(dao.voting, app, role);
        }
    }

    /// @dev The executor holds, or does not hold, each of `permissions`
    function _assertPermissions(Lido.Permission[] memory permissions, bool held) private view {
        for (uint256 i; i < permissions.length; ++i) {
            assertEq(
                acl.hasPermission(
                    evmScriptExecutor, permissions[i].app, Lido.roleId(permissions[i])
                ),
                held,
                string.concat(vm.getLabel(permissions[i].app), " ", permissions[i].role)
            );
        }
    }
}
