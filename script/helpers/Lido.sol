// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {
    IACL,
    IAragonApp,
    IKernel,
    ILidoLocator,
    IStakingRouter
} from "test/foundry/interfaces/External.sol";

/// @notice The Lido DAO by chain, what `utils/lido.py` holds for the Brownie scripts: the Aragon
///         apps the scripts deploy against and vote through, and the permissions an Easy Track
///         executor may hold on them
library Lido {
    struct DAO {
        uint256 chainId;
        /// @dev the deployment record of the Easy Track contracts, `deployed-<chain>.json`
        string deployedArtifact;
        address agent;
        address voting;
        address tokenManager;
        address finance;
        /// @dev the Aragon CallsScript the EVMScriptExecutor runs scripts through
        address callsScript;
        address ldo;
        address locator;
    }

    /// @dev `Permission`: an app and a role by the name of its `<ROLE>()` getter
    struct Permission {
        address app;
        string role;
    }

    uint256 internal constant CURATED_MODULE_ID = 1;

    /// @dev The DAO of the chain the script or the fork runs on
    function dao() internal view returns (DAO memory) {
        return dao(block.chainid);
    }

    /// @dev `addresses(network)`
    function dao(uint256 chainId) internal pure returns (DAO memory) {
        if (chainId == 560048) {
            return DAO({
                chainId: chainId,
                deployedArtifact: "deployed-hoodi.json",
                agent: 0x0534aA41907c9631fae990960bCC72d75fA7cfeD,
                voting: 0x49B3512c44891bef83F8967d075121Bd1b07a01B,
                tokenManager: 0x8ab4a56721Ad8e68c6Ad86F9D9929782A78E39E5,
                finance: 0x254Ae22bEEba64127F0e59fe8593082F3cd13f6b,
                callsScript: 0xfB3cB48d81eC8c7f2013a8dc9fA46D2D48112c3A,
                ldo: 0xEf2573966D009CcEA0Fc74451dee2193564198dc,
                locator: 0xe2EF9536DAAAEBFf5b1c130957AB3E80056b06D8
            });
        }

        if (chainId == 1) {
            return DAO({
                chainId: chainId,
                deployedArtifact: "deployed-mainnet.json",
                agent: 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c,
                voting: 0x2e59A20f205bB85a89C53f1936454680651E618e,
                tokenManager: 0xf73a1260d222f447210581DDf212D915c09a3249,
                finance: 0xB9E5CBB9CA5b0d659238807E84D0176930753d86,
                callsScript: 0x5cEb19e1890f677c3676d5ecDF7c501eBA01A054,
                ldo: 0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32,
                locator: 0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb
            });
        }

        revert("Lido: unknown chain id");
    }

    /// @dev The DAO ACL, through the Agent's kernel
    function acl(DAO memory self) internal view returns (IACL) {
        return IACL(IKernel(IAragonApp(self.agent).kernel()).acl());
    }

    /// @dev The curated node operators registry, the first module of the staking router
    function curatedRegistry(DAO memory self) internal view returns (address) {
        IStakingRouter router = IStakingRouter(ILidoLocator(self.locator).stakingRouter());

        return router.getStakingModule(CURATED_MODULE_ID).stakingModuleAddress;
    }

    /// @dev `required_permissions` of `scripts/grant_executor_permissions.py`: what the executor
    ///      needs to enact the scripts of the factories `DeployEasyTrack` registers
    function executorPermissions(DAO memory self) internal view returns (Permission[] memory) {
        Permission[] memory permissions = new Permission[](2);
        permissions[0] = Permission(self.finance, "CREATE_PAYMENTS_ROLE");
        permissions[1] = Permission(curatedRegistry(self), "SET_NODE_OPERATOR_LIMIT_ROLE");

        return permissions;
    }

    /// @dev `Permissions.all()`: every role of the six DAO apps
    function allPermissions(DAO memory self) internal view returns (Permission[] memory) {
        address lido = ILidoLocator(self.locator).lido();
        address registry = curatedRegistry(self);

        Permission[] memory permissions = new Permission[](29);
        permissions[0] = Permission(self.finance, "CREATE_PAYMENTS_ROLE");
        permissions[1] = Permission(self.finance, "CHANGE_PERIOD_ROLE");
        permissions[2] = Permission(self.finance, "CHANGE_BUDGETS_ROLE");
        permissions[3] = Permission(self.finance, "EXECUTE_PAYMENTS_ROLE");
        permissions[4] = Permission(self.finance, "MANAGE_PAYMENTS_ROLE");
        permissions[5] = Permission(self.agent, "ADD_PROTECTED_TOKEN_ROLE");
        permissions[6] = Permission(self.agent, "TRANSFER_ROLE");
        permissions[7] = Permission(self.agent, "RUN_SCRIPT_ROLE");
        permissions[8] = Permission(self.agent, "SAFE_EXECUTE_ROLE");
        permissions[9] = Permission(self.agent, "REMOVE_PROTECTED_TOKEN_ROLE");
        permissions[10] = Permission(self.agent, "DESIGNATE_SIGNER_ROLE");
        permissions[11] = Permission(self.agent, "EXECUTE_ROLE");
        permissions[12] = Permission(self.agent, "ADD_PRESIGNED_HASH_ROLE");
        permissions[13] = Permission(lido, "PAUSE_ROLE");
        permissions[14] = Permission(lido, "RESUME_ROLE");
        permissions[15] = Permission(lido, "STAKING_PAUSE_ROLE");
        permissions[16] = Permission(lido, "STAKING_CONTROL_ROLE");
        permissions[17] = Permission(registry, "STAKING_ROUTER_ROLE");
        permissions[18] = Permission(registry, "MANAGE_NODE_OPERATOR_ROLE");
        permissions[19] = Permission(registry, "MANAGE_SIGNING_KEYS");
        permissions[20] = Permission(registry, "SET_NODE_OPERATOR_LIMIT_ROLE");
        permissions[21] = Permission(self.tokenManager, "ISSUE_ROLE");
        permissions[22] = Permission(self.tokenManager, "ASSIGN_ROLE");
        permissions[23] = Permission(self.tokenManager, "BURN_ROLE");
        permissions[24] = Permission(self.tokenManager, "MINT_ROLE");
        permissions[25] = Permission(self.tokenManager, "REVOKE_VESTINGS_ROLE");
        permissions[26] = Permission(self.voting, "MODIFY_QUORUM_ROLE");
        permissions[27] = Permission(self.voting, "MODIFY_SUPPORT_ROLE");
        permissions[28] = Permission(self.voting, "CREATE_VOTES_ROLE");

        return permissions;
    }

    /// @dev `filter_granted`: the permissions of `permissions` the entity holds
    function granted(DAO memory self, address entity, Permission[] memory permissions)
        internal
        view
        returns (Permission[] memory)
    {
        return _select(self, entity, permissions, true);
    }

    /// @dev The permissions of `permissions` the entity lacks
    function missing(DAO memory self, address entity, Permission[] memory permissions)
        internal
        view
        returns (Permission[] memory)
    {
        return _select(self, entity, permissions, false);
    }

    /// @dev An Aragon role id is the hash of its name, what the app's `<ROLE>()` getter returns
    function roleId(Permission memory permission) internal pure returns (bytes32) {
        return keccak256(bytes(permission.role));
    }

    function _select(DAO memory self, address entity, Permission[] memory permissions, bool held)
        private
        view
        returns (Permission[] memory selected)
    {
        IACL acl_ = acl(self);
        uint256 count;

        selected = new Permission[](permissions.length);
        for (uint256 i; i < permissions.length; ++i) {
            if (acl_.hasPermission(entity, permissions[i].app, roleId(permissions[i])) == held) {
                selected[count++] = permissions[i];
            }
        }

        assembly ("memory-safe") {
            mstore(selected, count)
        }
    }
}
