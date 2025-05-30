// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../interfaces/IVaultHub.sol";
import "../interfaces/IStakingVault.sol";

/// @author dry914
/// @notice Adapter contract for forcing validator exits in VaultHub
contract ForceValidatorExitAdapter is TrustedCaller {
    // -------------
    // VARIABLES
    // -------------

    /// @notice The length of the public key in bytes
    uint256 private constant PUBLIC_KEY_LENGTH = 48;

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    /// @notice Address of EVMScriptExecutor
    address public immutable evmScriptExecutor;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _vaultHub,
        address _evmScriptExecutor
    ) TrustedCaller(_trustedCaller) {
        require(_vaultHub != address(0), "Zero VaultHub address");
        require(_evmScriptExecutor != address(0), "Zero EVMScriptExecutor address");
        
        vaultHub = IVaultHub(_vaultHub);
        evmScriptExecutor = _evmScriptExecutor;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Function to force validator exits in VaultHub
    /// @param _vault Address of the vault to exit validators from
    /// @param _pubkeys Public keys of the validators to exit
    function forceValidatorExits(
        address _vault,
        bytes calldata _pubkeys
    ) external payable {
        require(msg.sender == evmScriptExecutor, "Only EVMScriptExecutor");

        uint256 numKeys = _pubkeys.length / PUBLIC_KEY_LENGTH;
        uint256 value = IStakingVault(_vault).calculateValidatorWithdrawalFee(numKeys);

        try vaultHub.forceValidatorExits{value: value}(_vault, _pubkeys, address(this)) {} catch {}
    }

    /// @notice Function to withdraw all ETH to TrustedCaller
    function withdrawETH() external onlyTrustedCaller(msg.sender) {
        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH to withdraw");

        (bool success, ) = msg.sender.call{value: balance}("");
        require(success, "ETH transfer failed");
    }

    // -------------
    // RECEIVE
    // -------------

    receive() external payable {}
} 
