// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;


/**
 * @title VaultFactory
 * @author Lido
 * @notice The factory contract for StakingVaults
 */
interface IVaultFactory {
    struct RoleAssignment {
        address account;
        bytes32 role;
    }

    /**
     * @notice Creates a new StakingVault and Dashboard contracts
     * @param _defaultAdmin The address of the default admin of the Dashboard
     * @param _nodeOperator The address of the node operator of the StakingVault
     * @param _nodeOperatorManager The address of the node operator manager in the Dashboard
     * @param _nodeOperatorFeeBP The node operator fee in basis points
     * @param _confirmExpiry The confirmation expiry in seconds
     * @param _roleAssignments The optional role assignments to be made
     */
    function createVaultWithDashboard(
        address _defaultAdmin,
        address _nodeOperator,
        address _nodeOperatorManager,
        uint256 _nodeOperatorFeeBP,
        uint256 _confirmExpiry,
        RoleAssignment[] calldata _roleAssignments
    ) external payable returns (address vault, address dashboard);

    event VaultCreated(address vault);
}
