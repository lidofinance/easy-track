// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {
    IACL,
    ILidoLocator,
    IMiniMeToken,
    INodeOperatorsRegistry,
    IStakingRouter
} from "test/foundry/interfaces/External.sol";

/// @notice The votes `scripts/grant_executor_permissions.py` and
///         `scripts/revoke_all_permissions.py` open, replayed as Voting's calls on the live ACL
///         for a fresh executor: the grant of `CREATE_PAYMENTS_ROLE` on Finance and
///         `SET_NODE_OPERATOR_LIMIT_ROLE` on the curated registry, then their revocation, after
///         which the executor holds no permission of the six DAO apps. The setup vote first hands
///         Voting the manager slot of the registry role, so its votes may touch it.
contract ExecutorPermissionsTest is EasyTrackScenarioBase {
    /// @dev `utils/lido.py` `Permission`: an app and a role by its name
    struct Permission {
        address app;
        string name;
    }

    uint256 private constant CURATED_MODULE_ID = 1;

    IACL internal acl;
    address internal voting;
    address internal lido;
    address internal tokenManager;
    INodeOperatorsRegistry internal registry;

    /// @dev `required_permissions`
    Permission[] internal requiredPermissions;

    /// @dev `lido_permissions.all()`
    Permission[] internal allPermissions;

    function setUp() public {
        _forkAndInitialize();

        acl = _acl();
        voting = _voting();
        lido = ILidoLocator(config.locator).lido();
        tokenManager = IMiniMeToken(easyTrack.governanceToken()).controller();
        IStakingRouter stakingRouter = IStakingRouter(ILidoLocator(config.locator).stakingRouter());
        registry = INodeOperatorsRegistry(
            stakingRouter.getStakingModule(CURATED_MODULE_ID).stakingModuleAddress
        );

        vm.label(address(acl), "ACL");
        vm.label(voting, "Voting");
        vm.label(config.finance, "Finance");
        vm.label(lido, "Lido");
        vm.label(tokenManager, "TokenManager");
        vm.label(address(registry), "NodeOperatorsRegistry");

        _deployEasyTrack(address(this));
        _listPermissions();

        // The setup vote "Grant permission manager to Voting"
        bytes32 role = registry.SET_NODE_OPERATOR_LIMIT_ROLE();
        vm.prank(acl.getPermissionManager(address(registry), role));
        acl.setPermissionManager(voting, address(registry), role);
    }

    // python: test_grant_executor_permissions
    function testFork_GrantsExecutorPermissions() external {
        _assertPermissions(requiredPermissions, false);

        _grantByVote();

        _assertPermissions(requiredPermissions, true);
    }

    // python: test_revoke_permissions
    function testFork_RevokesAllPermissions() external {
        _grantByVote();

        _assertPermissions(requiredPermissions, true);

        _revokeByVote();

        _assertPermissions(allPermissions, false);
    }

    /// @dev `grant_executor_permissions`: the vote grants the executor every required permission
    function _grantByVote() private {
        vm.startPrank(voting);
        for (uint256 i; i < requiredPermissions.length; ++i) {
            acl.grantPermission(
                evmScriptExecutor, requiredPermissions[i].app, _role(requiredPermissions[i])
            );
        }
        vm.stopPrank();
    }

    /// @dev `revoke_permissions` of the granted permissions: the vote revokes each from the
    ///      executor
    function _revokeByVote() private {
        vm.startPrank(voting);
        for (uint256 i; i < requiredPermissions.length; ++i) {
            acl.revokePermission(
                evmScriptExecutor, requiredPermissions[i].app, _role(requiredPermissions[i])
            );
        }
        vm.stopPrank();
    }

    /// @dev The executor holds, or does not hold, each of `permissions`
    function _assertPermissions(Permission[] memory permissions, bool held) private view {
        for (uint256 i; i < permissions.length; ++i) {
            assertEq(
                acl.hasPermission(evmScriptExecutor, permissions[i].app, _role(permissions[i])),
                held,
                string.concat(vm.getLabel(permissions[i].app), " ", permissions[i].name)
            );
        }
    }

    /// @dev `lido_permissions`: the two required permissions and every role of the six apps
    function _listPermissions() private {
        requiredPermissions.push(Permission(config.finance, "CREATE_PAYMENTS_ROLE"));
        requiredPermissions.push(Permission(address(registry), "SET_NODE_OPERATOR_LIMIT_ROLE"));

        allPermissions.push(Permission(config.finance, "CREATE_PAYMENTS_ROLE"));
        allPermissions.push(Permission(config.finance, "CHANGE_PERIOD_ROLE"));
        allPermissions.push(Permission(config.finance, "CHANGE_BUDGETS_ROLE"));
        allPermissions.push(Permission(config.finance, "EXECUTE_PAYMENTS_ROLE"));
        allPermissions.push(Permission(config.finance, "MANAGE_PAYMENTS_ROLE"));

        allPermissions.push(Permission(config.agent, "ADD_PROTECTED_TOKEN_ROLE"));
        allPermissions.push(Permission(config.agent, "TRANSFER_ROLE"));
        allPermissions.push(Permission(config.agent, "RUN_SCRIPT_ROLE"));
        allPermissions.push(Permission(config.agent, "SAFE_EXECUTE_ROLE"));
        allPermissions.push(Permission(config.agent, "REMOVE_PROTECTED_TOKEN_ROLE"));
        allPermissions.push(Permission(config.agent, "DESIGNATE_SIGNER_ROLE"));
        allPermissions.push(Permission(config.agent, "EXECUTE_ROLE"));
        allPermissions.push(Permission(config.agent, "ADD_PRESIGNED_HASH_ROLE"));

        allPermissions.push(Permission(lido, "PAUSE_ROLE"));
        allPermissions.push(Permission(lido, "RESUME_ROLE"));
        allPermissions.push(Permission(lido, "STAKING_PAUSE_ROLE"));
        allPermissions.push(Permission(lido, "STAKING_CONTROL_ROLE"));

        allPermissions.push(Permission(address(registry), "STAKING_ROUTER_ROLE"));
        allPermissions.push(Permission(address(registry), "MANAGE_NODE_OPERATOR_ROLE"));
        allPermissions.push(Permission(address(registry), "MANAGE_SIGNING_KEYS"));
        allPermissions.push(Permission(address(registry), "SET_NODE_OPERATOR_LIMIT_ROLE"));

        allPermissions.push(Permission(tokenManager, "ISSUE_ROLE"));
        allPermissions.push(Permission(tokenManager, "ASSIGN_ROLE"));
        allPermissions.push(Permission(tokenManager, "BURN_ROLE"));
        allPermissions.push(Permission(tokenManager, "MINT_ROLE"));
        allPermissions.push(Permission(tokenManager, "REVOKE_VESTINGS_ROLE"));

        allPermissions.push(Permission(voting, "MODIFY_QUORUM_ROLE"));
        allPermissions.push(Permission(voting, "MODIFY_SUPPORT_ROLE"));
        allPermissions.push(Permission(voting, "CREATE_VOTES_ROLE"));
    }

    /// @dev An Aragon role id is the hash of its name, what the app's `<NAME>()` getter returns
    function _role(Permission memory permission) private pure returns (bytes32) {
        return keccak256(bytes(permission.name));
    }
}
