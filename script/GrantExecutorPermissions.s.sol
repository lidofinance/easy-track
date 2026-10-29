// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {console} from "forge-std/console.sol";
import {EasyTrackScript} from "script/helpers/EasyTrackScript.sol";
import {Lido} from "script/helpers/Lido.sol";
import {IACL} from "test/foundry/interfaces/External.sol";

/// @notice `scripts/grant_executor_permissions.py`: a vote granting an Easy Track executor the
///         permissions the factories of `DeployEasyTrack` need, `CREATE_PAYMENTS_ROLE` on
///         Finance and `SET_NODE_OPERATOR_LIMIT_ROLE` on the curated registry, the ones it does
///         not hold yet. `run` reads the executor from `EVM_SCRIPT_EXECUTOR` and opens the vote
///         from the broadcaster, who must hold LDO.
contract GrantExecutorPermissions is EasyTrackScript {
    function run() external {
        address executor = vm.envAddress("EVM_SCRIPT_EXECUTOR");
        Lido.Permission[] memory permissions = missingPermissions(executor);
        if (permissions.length == 0) {
            console.log("%s holds every required permission", executor);
            return;
        }

        vm.startBroadcast();
        uint256 voteId = createVote(executor, permissions);
        vm.stopBroadcast();

        console.log("vote %s grants %s permissions to %s", voteId, permissions.length, executor);
    }

    /// @dev `permissions_to_grant`: the required permissions the executor lacks
    function missingPermissions(address executor) public view returns (Lido.Permission[] memory) {
        Lido.DAO memory dao = Lido.dao();

        return Lido.missing(dao, executor, Lido.executorPermissions(dao));
    }

    /// @dev `grant_executor_permissions`: open the vote granting the executor `permissions`
    function createVote(address executor, Lido.Permission[] memory permissions)
        public
        returns (uint256)
    {
        Lido.DAO memory dao = Lido.dao();

        return _createVote(
            dao,
            _encodePermissionsScript(dao, IACL.grantPermission.selector, executor, permissions),
            string.concat("Grant permissions to ", vm.toString(executor))
        );
    }
}
