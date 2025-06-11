// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Adapter for decreasing share limits in VaultHub
contract DecreaseShareLimitsAdapter {
    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    /// @notice Address of the EVMScriptExecutor
    address public immutable evmScriptExecutor;

    // -------------
    // EVENTS
    // -------------

    event ShareLimitUpdateFailed(address indexed vault, uint256 shareLimit);

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _vaultHub, address _evmScriptExecutor) {
        require(_vaultHub != address(0), "Zero VaultHub address");
        require(_evmScriptExecutor != address(0), "Zero EVMScriptExecutor address");

        vaultHub = IVaultHub(_vaultHub);
        evmScriptExecutor = _evmScriptExecutor;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Updates share limit for a vault
    /// @param _vault address of the vault to update
    /// @param _shareLimit new share limit value
    function updateShareLimit(address _vault, uint256 _shareLimit) external {
        require(msg.sender == evmScriptExecutor, "Only EVMScriptExecutor");

        if (_shareLimit > vaultHub.vaultConnection(_vault).shareLimit) {
            emit ShareLimitUpdateFailed(_vault, _shareLimit);
            return;
        }

        try vaultHub.updateShareLimit(_vault, _shareLimit) {
        } catch {
            emit ShareLimitUpdateFailed(_vault, _shareLimit);
        }
    }
} 
