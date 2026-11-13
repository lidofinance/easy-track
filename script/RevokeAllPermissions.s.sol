// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {console} from "forge-std/console.sol";
import {EasyTrackScript} from "script/helpers/EasyTrackScript.sol";
import {Lido} from "script/helpers/Lido.sol";
import {IACL} from "test/foundry/interfaces/External.sol";

/// @notice `scripts/revoke_all_permissions.py`: a vote revoking every permission an Easy Track
///         executor holds on the six DAO apps. `run` reads the executor from
///         `EVM_SCRIPT_EXECUTOR` and opens the vote from the broadcaster, who must hold LDO.
contract RevokeAllPermissions is EasyTrackScript {
    function run() external {
        address executor = vm.envAddress("EVM_SCRIPT_EXECUTOR");
        Lido.Permission[] memory permissions = grantedPermissions(executor);
        if (permissions.length == 0) {
            console.log("%s holds no permission", executor);
            return;
        }

        vm.startBroadcast();
        uint256 voteId = createVote(executor, permissions);
        vm.stopBroadcast();

        console.log("vote %s revokes %s permissions from %s", voteId, permissions.length, executor);
    }

    /// @dev `granted_permissions`: the permissions of the six apps the executor holds
    function grantedPermissions(address executor) public view returns (Lido.Permission[] memory) {
        Lido.DAO memory dao = Lido.dao();

        return Lido.granted(dao, executor, Lido.allPermissions(dao));
    }

    /// @dev `revoke_permissions`: open the vote revoking `permissions` from the executor
    function createVote(address executor, Lido.Permission[] memory permissions)
        public
        returns (uint256)
    {
        Lido.DAO memory dao = Lido.dao();

        return _createVote(
            dao,
            _encodePermissionsScript(dao, IACL.revokePermission.selector, executor, permissions),
            string.concat("Revoke all permissions from ", vm.toString(executor))
        );
    }
}
