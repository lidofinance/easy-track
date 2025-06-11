// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Adapter for socializing bad debt in VaultHub
contract SocializeBadDebtAdapter {
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

    event BadDebtSocializationFailed(address indexed badDebtVault, address indexed vaultAcceptor, uint256 maxSharesToSocialize);

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

    /// @notice Socializes bad debt for a vault
    /// @param _badDebtVault address of the vault that has the bad debt
    /// @param _vaultAcceptor address of the vault that will accept the bad debt or 0 if the bad debt is internalized to the protocol
    /// @param _maxSharesToSocialize maximum amount of shares to socialize
    function socializeBadDebt(
        address _badDebtVault,
        address _vaultAcceptor,
        uint256 _maxSharesToSocialize
    ) external {
        require(msg.sender == evmScriptExecutor, "Only EVMScriptExecutor");

        try vaultHub.socializeBadDebt(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize) {
        } catch {
            emit BadDebtSocializationFailed(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize);
        }
    }
} 
