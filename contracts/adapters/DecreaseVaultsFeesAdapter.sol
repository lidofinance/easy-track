// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Adapter contract for updating vault fees in VaultHub
contract DecreaseVaultsFeesAdapter {
    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    /// @notice Address of EVMScriptExecutor
    address public immutable evmScriptExecutor;

    // -------------
    // EVENTS
    // -------------

    event VaultFeesUpdateFailed(address indexed vault, uint256 infraFeeBP, uint256 liquidityFeeBP, uint256 reservationFeeBP);

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _vaultHub,
        address _evmScriptExecutor
    ) {
        require(_vaultHub != address(0), "Zero VaultHub address");
        require(_evmScriptExecutor != address(0), "Zero EVMScriptExecutor address");
        
        vaultHub = IVaultHub(_vaultHub);
        evmScriptExecutor = _evmScriptExecutor;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Function to update vault fees in VaultHub
    /// @param _vault Address of the vault to update fees for
    /// @param _infraFeeBP New infra fee in basis points
    /// @param _liquidityFeeBP New liquidity fee in basis points
    /// @param _reservationFeeBP New reservation fee in basis points
    function updateVaultFees(
        address _vault,
        uint256 _infraFeeBP,
        uint256 _liquidityFeeBP,
        uint256 _reservationFeeBP
    ) external {
        require(msg.sender == evmScriptExecutor, "Only EVMScriptExecutor");

        IVaultHub.VaultConnection memory connection = vaultHub.vaultConnection(_vault);
        if (_infraFeeBP > connection.infraFeeBP ||
            _liquidityFeeBP > connection.liquidityFeeBP ||
            _reservationFeeBP > connection.reservationFeeBP) {
            emit VaultFeesUpdateFailed(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
            return;
        }

        try vaultHub.updateVaultFees(
            _vault,
            _infraFeeBP,
            _liquidityFeeBP,
            _reservationFeeBP
        ) {} catch {
            emit VaultFeesUpdateFailed(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
        }
    }
}
