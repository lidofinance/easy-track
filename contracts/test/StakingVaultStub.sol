// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IStakingVault.sol";

/// @author dry914
/// @notice Stub contract for testing IStakingVault interface
contract StakingVaultStub is IStakingVault {
    // -------------
    // VARIABLES
    // -------------

    /// @notice Fee per validator in wei
    uint256 public constant VALIDATOR_WITHDRAWAL_FEE = 0.1 ether;

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Calculates fee for validator withdrawal
    /// @param _numKeys Number of validators to exit
    /// @return Fee amount in wei
    function calculateValidatorWithdrawalFee(uint256 _numKeys) external pure override returns (uint256) {
        return _numKeys * VALIDATOR_WITHDRAWAL_FEE;
    }
} 
