// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {SimpleDvtScenarioBase} from "test/foundry/helpers/SimpleDvtScenarioBase.sol";
import {IEVMScriptExecutor} from "test/foundry/interfaces/EasyTrack.sol";
import {IACL} from "test/foundry/interfaces/External.sol";

/// @notice The deployed `AddNodeOperators` and `ChangeNodeOperatorManagers` of
///         `deployed-<chain>.json` around a DAO vote that grants the Agent `MANAGE_SIGNING_KEYS`:
///         the executor stays the permission manager, so motions keep changing managers
contract SimpleDvtSigningKeysRoleTest is SimpleDvtScenarioBase {
    uint256 internal constant CLUSTERS_COUNT = 7;

    /// @dev Index of the cluster handed to a new manager
    uint256 internal constant OPERATOR_5 = 5;

    // python: test_simple_make_action
    function testFork_ChangesManagerAfterAgentIsGrantedSigningKeysRole() external {
        _enact(addNodeOperators, creator, _encodeAddClusters(CLUSTERS_COUNT));

        for (uint256 index; index < CLUSTERS_COUNT; ++index) {
            _assertClusterAdded(index);
        }

        // The executor, as the permission manager, grants the Agent the role on the DAO's behalf
        _executeDaoScript(
            address(acl),
            abi.encodeCall(
                IACL.grantPermission, (config.agent, address(simpleDvt), MANAGE_SIGNING_KEYS)
            )
        );

        assertEq(
            acl.getPermissionManager(address(simpleDvt), MANAGE_SIGNING_KEYS),
            evmScriptExecutor,
            "getPermissionManager"
        );
        assertTrue(
            acl.hasPermission(config.agent, address(simpleDvt), MANAGE_SIGNING_KEYS),
            "agent hasPermission"
        );
        assertEq(IEVMScriptExecutor(evmScriptExecutor).easyTrack(), address(easyTrack), "easyTrack");

        _enact(
            changeNodeOperatorManagers,
            creator,
            _encodeChangeManager(_operatorId(OPERATOR_5), _operatorAddress(OPERATOR_5), stranger)
        );

        assertFalse(
            _canManageSigningKeys(_operatorAddress(OPERATOR_5), _operatorId(OPERATOR_5)),
            "old manager canPerform"
        );
        assertTrue(
            _canManageSigningKeys(stranger, _operatorId(OPERATOR_5)), "new manager canPerform"
        );
    }
}
